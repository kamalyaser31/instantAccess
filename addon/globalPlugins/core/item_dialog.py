import os
import shutil

import addonHandler
import gui
from gui import guiHelper, nvdaControls
import wx

from .command_picker_dialog import NvdaCommandPickerDialog
from .constants import (
	ADDON_SCRIPT_GESTURES,
	ALL_FILES_WILDCARD,
	ANNOUNCE_LABELS,
	ANNOUNCE_VALUES,
	CONFIRM_CAPTION,
	ERROR_CAPTION,
	RESERVED_GESTURES,
	TEXT_SNIPPET_ACTION_LABELS,
	TEXT_SNIPPET_ACTION_TO_LABEL,
	TEXT_SNIPPET_ACTION_VALUES,
	TYPE_LABELS,
	TYPE_SECTIONS,
	TYPE_TO_LABEL,
)
from .executor import expandPath, isValidKeystroke
from .placeholders import actionNeedsContext
from .timing import parseDelay
from .gestures import (
	gestureToKeystroke,
	parseAppNames,
	buildGestureNameFromEvent,
	formatGestureForDisplay,
	gestureDisplayText,
	gestureKey,
	getAddonGestures,
	normalizeGesture,
	validateGestureName,
)

addonHandler.initTranslation()


def _formatDelay(delayValue):
	try:
		number = parseDelay(delayValue)
	except ValueError:
		number = 0.0
	return f"{number:.3f}".rstrip("0").rstrip(".") or "0"


def parseDelayField(rawValue, invalidMessage, negativeMessage, default="0"):
	"""Parse a delay field; show the matching error and return None when it is not a valid delay."""
	text = (rawValue or default).strip()
	try:
		return parseDelay(text)
	except ValueError:
		try:
			isNegative = float(text) < 0
		except ValueError:
			isNegative = False
		gui.messageBox(negativeMessage if isNegative else invalidMessage, ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
		return None


def actionDetails(action, maxLength=50):
	"""One-line description of an action for lists, cut to maxLength characters."""
	itemType = action.get("type", "")
	if itemType in ("TextSnippets", "Keystrokes"):
		lines = (action.get("path", "") or "").splitlines()
		firstLine = lines[0].strip() if lines else ""
		if len(firstLine) > maxLength:
			firstLine = firstLine[: maxLength - 3] + "..."
		if itemType == "Keystrokes":
			return firstLine
		actionLabel = TEXT_SNIPPET_ACTION_TO_LABEL.get(
			action.get("textAction", "type"),
			TEXT_SNIPPET_ACTION_TO_LABEL["type"],
		)
		# Translators: Summary of a text snippet action, e.g. "Paste: Hello".
		return _("{action}: {preview}").format(action=actionLabel, preview=firstLine)
	if itemType == "NvdaCommands":
		return action.get("commandLabel", "") or action.get("path", "")
	details = action.get("path", "")
	arguments = (action.get("arguments", "") or "").strip()
	if itemType == "Programs" and arguments:
		details = f"{details} {arguments}"
	return details


def _getActionSummary(action):
	itemType = action.get("type", "")
	typeLabel = TYPE_TO_LABEL.get(itemType, itemType).replace("&", "")
	return typeLabel, _formatDelay(action.get("delay", 0.0)), actionDetails(action)


def _labeledRow(parent, labelText, makeControl, makeButton=None, proportion=1, labelFlag=None, controlFlag=0):
	"""Build label, control and optional button in one flat row.

	The label is created first so NVDA reads it as the control's name. The row stays flat,
	because _setRowVisible shows and hides only the row's direct child windows.
	"""
	if labelFlag is None:
		labelFlag = wx.ALIGN_CENTER_VERTICAL
	space = guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL
	row = wx.BoxSizer(wx.HORIZONTAL)
	label = wx.StaticText(parent, wx.ID_ANY, labelText)
	row.Add(label, 0, labelFlag | wx.RIGHT, space)
	control = makeControl()
	button = makeButton() if makeButton else None
	if button:
		row.Add(control, proportion, controlFlag | wx.RIGHT, space)
		row.Add(button, 0)
	else:
		row.Add(control, proportion, controlFlag)
	return row, label, control, button


SWITCH_DELAY_SECONDS = 3


def actionsNeedSwitchDelay(actions):
	"""True when an action types, sends keys or reads the target window, so the user must reach it first."""
	for action in actions:
		if actionNeedsContext(action):
			return True
		itemType = action.get("type", "")
		if itemType == "Keystrokes":
			return True
		if itemType == "TextSnippets" and action.get("textAction", "type") in ("type", "paste"):
			return True
	return False


def confirmSwitchDelay():
	# Translators: Prompt confirming test of keystroke simulation or text typing with a switch delay.
	msg = _(
		"Keystrokes or text typing will be simulated after a 3-second delay so you can switch to the target window.\n\n"
		"Would you like to proceed?",
	)
	return gui.messageBox(msg, CONFIRM_CAPTION, wx.YES_NO | wx.ICON_QUESTION) == wx.YES


class ShortcutCaptureDialog(wx.Dialog):
	def __init__(self, parent):
		# Translators: Title of the dialog that captures an item's shortcut.
		wx.Dialog.__init__(self, parent, title=_("Set shortcut"), style=wx.DEFAULT_DIALOG_STYLE)
		self.gestureName = ""
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		# Translators: Instruction in the shortcut capture dialog.
		label = wx.StaticText(self, wx.ID_ANY, _("Press the desired shortcut key. Escape cancels."))
		mainSizer.Add(label, 0, wx.ALL, 10)
		self.SetSizerAndFit(mainSizer)
		self.Bind(wx.EVT_CHAR_HOOK, self.onKeyPress)
		self.CentreOnScreen()

	def onKeyPress(self, event):
		if event.GetKeyCode() == wx.WXK_ESCAPE:
			self.EndModal(wx.ID_CANCEL)
			return
		gestureName = buildGestureNameFromEvent(event)
		if not gestureName:
			return
		self.gestureName = gestureName
		self.EndModal(wx.ID_OK)


class InstantAccessActionDialog(wx.Dialog):
	def __init__(self, parent, title, existingAction=None):
		wx.Dialog.__init__(self, parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
		self.selectedCommandId = ""
		self.selectedCommandLabel = ""
		self.executionQueue = getattr(parent, "executionQueue", None)

		mainSizer = wx.BoxSizer(wx.VERTICAL)
		sizerHelper = guiHelper.BoxSizerHelper(self, wx.VERTICAL)

		# Translators: Label of the action type choice.
		self.typeChoice = sizerHelper.addLabeledControl(_("Type"), wx.Choice, choices=TYPE_LABELS)
		self.typeChoice.SetSelection(0)

		self.pathRow, self.pathLabel, self.pathCtrl, self.browseButton = _labeledRow(
			self,
			# Translators: Label of the path or URL field in the action dialog.
			_("Path or URL"),
			lambda: wx.TextCtrl(self, wx.ID_ANY),
			# Translators: Button that opens a file or folder chooser for the action path.
			lambda: wx.Button(self, wx.ID_ANY, _("Browse")),
		)
		# Translators: Button to open a menu of variables to insert into the path or URL field.
		self.pathInsertVarButton = wx.Button(self, wx.ID_ANY, _("Insert &variable…"))
		self.pathRow.Add(self.pathInsertVarButton, 0)
		sizerHelper.addItem(self.pathRow, flag=wx.EXPAND)

		self.argumentsRow, self.argumentsLabel, self.argumentsCtrl, _unused = _labeledRow(
			self,
			# Translators: Label of the optional command line arguments field.
			_("Arguments (optional)"),
			lambda: wx.TextCtrl(self, wx.ID_ANY),
		)
		# Translators: Button to open a menu of variables to insert into the arguments field.
		self.argsInsertVarButton = wx.Button(self, wx.ID_ANY, _("Insert &variable…"))
		self.argumentsRow.Add(self.argsInsertVarButton, 0)
		sizerHelper.addItem(self.argumentsRow, flag=wx.EXPAND)

		# Translators: Checkbox that starts a program with administrator rights.
		self.runAsAdminCheck = wx.CheckBox(self, wx.ID_ANY, _("Run as &administrator"))
		sizerHelper.addItem(self.runAsAdminCheck)

		self.commandRow, self.commandLabel, self.commandCtrl, self.commandButton = _labeledRow(
			self,
			# Translators: Label of the read-only field showing the chosen NVDA command.
			_("NVDA command"),
			lambda: wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY),
			# Translators: Button that opens the NVDA command picker.
			lambda: wx.Button(self, wx.ID_ANY, _("Select command")),
		)
		sizerHelper.addItem(self.commandRow, flag=wx.EXPAND)

		self.snippetRow, self.snippetLabel, self.snippetCtrl, self.addKeystrokeButton = _labeledRow(
			self,
			# Translators: Label of the text snippet field.
			_("Text snippet"),
			lambda: wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_MULTILINE, size=(-1, 120)),
			# Translators: Button that captures a key press and adds it to the keystrokes field.
			lambda: wx.Button(self, wx.ID_ANY, _("Add keystroke")),
			labelFlag=wx.ALIGN_TOP,
			controlFlag=wx.EXPAND,
		)
		# Translators: Button to open a menu of variables to insert into the snippet field.
		self.snippetInsertVarButton = wx.Button(self, wx.ID_ANY, _("Insert &variable…"))
		self.snippetRow.Add(self.snippetInsertVarButton, 0)
		sizerHelper.addItem(self.snippetRow, flag=wx.EXPAND)

		self.snippetActionRow, self.snippetActionLabel, self.snippetActionChoice, _unused = _labeledRow(
			self,
			# Translators: Label of the choice between typing, copying and pasting a snippet.
			_("Snippet action"),
			lambda: wx.Choice(self, wx.ID_ANY, choices=TEXT_SNIPPET_ACTION_LABELS),
			proportion=0,
		)
		self.snippetActionChoice.SetSelection(0)
		sizerHelper.addItem(self.snippetActionRow, flag=wx.EXPAND)
		self.typingDelayRow, self.typingDelayLabel, self.typingDelayCtrl, _unused = _labeledRow(
			self,
			# Translators: Label of the delay between typed characters.
			_("Typing delay"),
			lambda: wx.TextCtrl(self, wx.ID_ANY),
			proportion=0,
		)
		sizerHelper.addItem(self.typingDelayRow, flag=wx.EXPAND)
		self.typingDelayCtrl.SetValue("0.05")

		self.delayCtrl = sizerHelper.addLabeledControl(
			# Translators: Label of the delay before this action runs.
			_("Delay before executing this action (seconds)"),
			wx.TextCtrl,
		)
		self.delayCtrl.SetValue("0")

		buttonSizer = guiHelper.ButtonHelper(wx.HORIZONTAL)
		# Translators: OK button of the action dialog.
		self.okButton = buttonSizer.addButton(self, wx.ID_OK, _("&OK"))
		# Translators: Cancel button of the action dialog.
		buttonSizer.addButton(self, wx.ID_CANCEL, _("&Cancel"))
		# Translators: Button that runs only this action, to try it.
		self.testButton = buttonSizer.addButton(self, label=_("&Test"))

		mainSizer.Add(sizerHelper.sizer, 1, wx.ALL | wx.EXPAND, 10)
		mainSizer.Add(buttonSizer.sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)
		self.SetSizerAndFit(mainSizer)
		self.SetMinSize((560, 460))

		self.typeChoice.Bind(wx.EVT_CHOICE, self.onTypeChange)
		self.snippetActionChoice.Bind(wx.EVT_CHOICE, self.onSnippetActionChange)
		self.browseButton.Bind(wx.EVT_BUTTON, self.onBrowse)
		self.commandButton.Bind(wx.EVT_BUTTON, self.onSelectCommand)
		self.addKeystrokeButton.Bind(wx.EVT_BUTTON, self.onAddKeystroke)
		self.pathInsertVarButton.Bind(wx.EVT_BUTTON, lambda evt: self.onInsertVariable(self.pathCtrl))
		self.argsInsertVarButton.Bind(wx.EVT_BUTTON, lambda evt: self.onInsertVariable(self.argumentsCtrl))
		self.snippetInsertVarButton.Bind(wx.EVT_BUTTON, lambda evt: self.onInsertVariable(self.snippetCtrl))
		self.okButton.Bind(wx.EVT_BUTTON, self.onOk)
		self.testButton.Bind(wx.EVT_BUTTON, self.onTestAction)

		if existingAction:
			self._loadExistingAction(existingAction)

		self.updateTypeState()
		self.CentreOnScreen()

	def _setRowVisible(self, row, visible):
		for child in row.GetChildren():
			if child.IsWindow():
				child.GetWindow().Show(visible)

	def _loadExistingAction(self, action):
		itemType = action.get("type", TYPE_SECTIONS[0])
		if itemType in TYPE_SECTIONS:
			self.typeChoice.SetSelection(TYPE_SECTIONS.index(itemType))
		self.pathCtrl.SetValue(action.get("path", ""))
		self.argumentsCtrl.SetValue(action.get("arguments", ""))
		self.runAsAdminCheck.SetValue(bool(action.get("runAsAdmin", False)))
		self.selectedCommandId = action.get("path", "") if itemType == "NvdaCommands" else ""
		self.selectedCommandLabel = action.get("commandLabel", "")
		if self.selectedCommandLabel:
			self.commandCtrl.SetValue(self.selectedCommandLabel)
		if itemType in ("TextSnippets", "Keystrokes"):
			self.snippetCtrl.SetValue(action.get("path", ""))
		else:
			self.snippetCtrl.SetValue("")
		actionValue = (action.get("textAction", TEXT_SNIPPET_ACTION_VALUES[0]) or "").strip().lower()
		if actionValue in TEXT_SNIPPET_ACTION_VALUES:
			self.snippetActionChoice.SetSelection(TEXT_SNIPPET_ACTION_VALUES.index(actionValue))
		if itemType == "Keystrokes":
			self.typingDelayCtrl.SetValue(_formatDelay(action.get("pressDelay", 0.05)))
		else:
			self.typingDelayCtrl.SetValue(_formatDelay(action.get("typingDelay", 0.05)))
		self.delayCtrl.SetValue(_formatDelay(action.get("delay", 0.0)))

	def updateTypeState(self):
		itemType = TYPE_SECTIONS[self.typeChoice.GetSelection()]
		showPath = itemType in ("Websites", "Programs", "Folders", "Files")
		showArguments = itemType == "Programs"
		showCommand = itemType == "NvdaCommands"
		showSnippetArea = itemType in ("TextSnippets", "Keystrokes")
		showSnippetActionChoice = itemType == "TextSnippets"
		showDelayField = (
			itemType == "TextSnippets"
			and TEXT_SNIPPET_ACTION_VALUES[self.snippetActionChoice.GetSelection()] == "type"
		) or itemType == "Keystrokes"

		# Labels change at runtime to match the currently selected action type.
		if itemType == "Keystrokes":
			# Translators: Label of the keystrokes field; one key or shortcut per line.
			self.snippetLabel.SetLabel(_("Keystrokes (one per line, e.g. 'down 5')"))
			# Translators: Label of the delay between simulated key presses.
			self.typingDelayLabel.SetLabel(_("Delay between keystrokes (seconds)"))
		else:
			# Translators: Label of the text snippet field.
			self.snippetLabel.SetLabel(_("Text snippet"))
			# Translators: Label of the delay between typed characters.
			self.typingDelayLabel.SetLabel(_("Typing delay"))

		self._setRowVisible(self.pathRow, showPath)
		self.browseButton.Show(itemType in ("Programs", "Folders", "Files"))
		self.pathInsertVarButton.Show(itemType == "Websites")
		self._setRowVisible(self.argumentsRow, showArguments)
		self.argsInsertVarButton.Show(showArguments)
		self.runAsAdminCheck.Show(showArguments)
		self._setRowVisible(self.commandRow, showCommand)
		self._setRowVisible(self.snippetRow, showSnippetArea)
		self.addKeystrokeButton.Show(itemType == "Keystrokes")
		self.snippetInsertVarButton.Show(itemType == "TextSnippets")
		self._setRowVisible(self.snippetActionRow, showSnippetActionChoice)
		self._setRowVisible(self.typingDelayRow, showDelayField)
		self.Layout()

	def onInsertVariable(self, targetCtrl):
		menu = wx.Menu()
		entries = [
			# Translators: Menu item to insert the {date} variable into the text field.
			(_("&Date"), "{date}"),
			# Translators: Menu item to insert the {time} variable into the text field.
			(_("&Time"), "{time}"),
			# Translators: Menu item to insert the {clipboard} variable into the text field.
			(_("&Clipboard text"), "{clipboard}"),
			# Translators: Menu item to insert the {selection} variable into the text field.
			(_("&Selected text"), "{selection}"),
			# Translators: Menu item to insert the {file} variable into the text field.
			(_("Selected &file (File Explorer)"), "{file}"),
			# Translators: Menu item to insert the {folder} variable into the text field.
			(_("Open f&older (File Explorer)"), "{folder}"),
		]
		for label, placeholder in entries:
			item = menu.Append(wx.ID_ANY, label)
			self.Bind(
				wx.EVT_MENU,
				lambda evt, p=placeholder, c=targetCtrl: self._insertPlaceholder(c, p),
				item,
			)
		self.PopupMenu(menu)
		menu.Destroy()

	def _insertPlaceholder(self, targetCtrl, placeholder):
		targetCtrl.WriteText(placeholder)
		targetCtrl.SetFocus()

	def onTypeChange(self, event):
		self.updateTypeState()

	def onSnippetActionChange(self, event):
		self.updateTypeState()

	def onBrowse(self, event):
		itemType = TYPE_SECTIONS[self.typeChoice.GetSelection()]
		if itemType == "Folders":
			# Translators: Title of the folder chooser.
			dialog = wx.DirDialog(self, _("Select a folder"), style=wx.DD_DIR_MUST_EXIST)
		elif itemType in ("Programs", "Files"):
			# Translators: Titles of the program and file choosers.
			title = _("Select a program") if itemType == "Programs" else _("Select a file")
			dialog = wx.FileDialog(
				self,
				title,
				wildcard=ALL_FILES_WILDCARD,
				style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
			)
		else:
			return
		if dialog.ShowModal() == wx.ID_OK:
			self.pathCtrl.SetValue(dialog.GetPath())
		dialog.Destroy()

	def onAddKeystroke(self, event):
		dialog = ShortcutCaptureDialog(self)
		if dialog.ShowModal() == wx.ID_OK:
			keystroke = gestureToKeystroke(dialog.gestureName)
			if isValidKeystroke(keystroke):
				text = self.snippetCtrl.GetValue()
				if text and not text.endswith("\n"):
					text += "\n"
				self.snippetCtrl.SetValue(text + keystroke)
			else:
				# Translators: Error shown when a captured key cannot be sent by a keystrokes action.
				gui.messageBox(_("Invalid shortcut key."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
		dialog.Destroy()

	def onSelectCommand(self, event):
		dialog = NvdaCommandPickerDialog(self, selectedCommandId=self.selectedCommandId)
		if dialog.ShowModal() == wx.ID_OK:
			self.selectedCommandId = dialog.result["commandId"]
			self.selectedCommandLabel = dialog.result["commandLabel"]
			self.commandCtrl.SetValue(self.selectedCommandLabel)
		dialog.Destroy()

	def validate(self, isTesting=False):
		itemType = TYPE_SECTIONS[self.typeChoice.GetSelection()]
		arguments = self.argumentsCtrl.GetValue().strip() if itemType == "Programs" else ""
		textAction = TEXT_SNIPPET_ACTION_VALUES[self.snippetActionChoice.GetSelection()]

		if itemType in ("TextSnippets", "Keystrokes"):
			path = self.snippetCtrl.GetValue()
		elif itemType == "NvdaCommands":
			path = self.selectedCommandId.strip()
		else:
			path = self.pathCtrl.GetValue().strip().strip("'\"")

		if not path.strip():
			# Translators: Error shown when the action's main field is empty.
			gui.messageBox(_("All fields are required."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None

		if not isTesting and itemType in ("Programs", "Folders", "Files"):
			resolved = expandPath(path)
			exists = os.path.exists(resolved)
			if not exists and itemType == "Programs":
				exists = bool(shutil.which(resolved))
			if not exists:
				# Translators: Warning message shown when an action path does not exist on disk or in PATH.
				warnMsg = _(
					"The specified path was not found on your system:\n{path}\n\n"
					"Would you like to save this action anyway?",
				).format(path=path)
				if gui.messageBox(warnMsg, CONFIRM_CAPTION, wx.YES_NO | wx.ICON_QUESTION) != wx.YES:
					return None

		delay = parseDelayField(
			self.delayCtrl.GetValue(),
			# Translators: Error shown when the action delay is not a number.
			_("Delay must be a valid number."),
			# Translators: Error shown when the action delay is negative.
			_("Delay must be zero or greater."),
		)
		if delay is None:
			return None

		typingDelay = 0.05
		pressDelay = 0.05

		if itemType == "TextSnippets" and textAction == "type":
			parsed = parseDelayField(
				self.typingDelayCtrl.GetValue(),
				# Translators: Error shown when the typing delay is not a number.
				_("Typing delay must be a valid number."),
				# Translators: Error shown when the typing delay is negative.
				_("Typing delay must be zero or greater."),
				default="0.05",
			)
			if parsed is None:
				return None
			typingDelay = parsed

		elif itemType == "Keystrokes":
			parsed = parseDelayField(
				self.typingDelayCtrl.GetValue(),
				# Translators: Error shown when the keystroke delay is not a number.
				_("Delay between keystrokes must be a valid number."),
				# Translators: Error shown when the keystroke delay is negative.
				_("Delay between keystrokes must be zero or greater."),
				default="0.05",
			)
			if parsed is None:
				return None
			pressDelay = parsed

		return {
			"type": itemType,
			"path": path,
			"arguments": arguments,
			"runAsAdmin": itemType == "Programs" and self.runAsAdminCheck.GetValue(),
			"textAction": textAction,
			"typingDelay": typingDelay,
			"pressDelay": pressDelay,
			"commandLabel": self.selectedCommandLabel.strip(),
			"delay": delay,
		}

	def onTestAction(self, event):
		result = self.validate(isTesting=True)
		if not result:
			return
		needsSwitchDelay = actionsNeedSwitchDelay([result])
		if needsSwitchDelay and not confirmSwitchDelay():
			return

		if self.executionQueue is not None:
			self.executionQueue.submit(
				{"actions": [result], "stopOnError": True},
				preDelay=SWITCH_DELAY_SECONDS if needsSwitchDelay else 0,
			)

	def onOk(self, event):
		result = self.validate()
		if not result:
			return
		self.result = result
		self.EndModal(wx.ID_OK)


class InstantAccessItemDialog(wx.Dialog):
	def __init__(self, parent, configManager, title, existingItem=None):
		wx.Dialog.__init__(self, parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
		self.configManager = configManager
		self.executionQueue = getattr(parent, "executionQueue", None)
		self.getPreviousAppName = getattr(parent, "getPreviousAppName", None)
		self.existingItem = existingItem
		self.gesture = ""
		self.actions = []

		mainSizer = wx.BoxSizer(wx.VERTICAL)
		sizerHelper = guiHelper.BoxSizerHelper(self, wx.VERTICAL)

		# Translators: Label of the item name field.
		self.nameCtrl = sizerHelper.addLabeledControl(_("Name"), wx.TextCtrl)

		# Translators: Label of the item's action list.
		actionsLabel = wx.StaticText(self, wx.ID_ANY, _("Actions"))
		sizerHelper.addItem(actionsLabel)
		self.actionsList = nvdaControls.AutoWidthColumnListCtrl(
			self,
			style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN,
		)
		# Translators: Column header for the action type.
		self.actionsList.InsertColumn(0, _("Type"))
		# Translators: Column header for the delay before an action.
		self.actionsList.InsertColumn(1, _("Delay"))
		# Translators: Column header for the action details.
		self.actionsList.InsertColumn(2, _("Details"))
		sizerHelper.addItem(self.actionsList, flag=wx.EXPAND, proportion=1)

		actionsButtons = guiHelper.ButtonHelper(wx.HORIZONTAL)
		# Translators: Button that adds an action.
		self.addActionButton = actionsButtons.addButton(self, label=_("&Add"))
		# Translators: Button that edits the selected action.
		self.editActionButton = actionsButtons.addButton(self, label=_("&Edit"))
		# Translators: Button that deletes the selected action.
		self.deleteActionButton = actionsButtons.addButton(self, label=_("&Delete"))
		# Translators: Button that moves the selected action up.
		self.moveUpActionButton = actionsButtons.addButton(self, label=_("Move &up"))
		# Translators: Button that moves the selected action down.
		self.moveDownActionButton = actionsButtons.addButton(self, label=_("Move do&wn"))
		sizerHelper.addItem(actionsButtons.sizer, flag=wx.EXPAND)

		self.intervalCtrl = sizerHelper.addLabeledControl(
			# Translators: Label of the pause between the item's actions.
			_("Interval between actions (seconds)"),
			wx.TextCtrl,
		)
		self.intervalCtrl.SetValue("0")

		self.stopOnErrorCheck = wx.CheckBox(
			self,
			wx.ID_ANY,
			# Translators: Checkbox that stops the item when one of its actions fails.
			_("Stop executing remaining actions if an action fails"),
		)
		self.stopOnErrorCheck.SetValue(True)
		sizerHelper.addItem(self.stopOnErrorCheck)

		self.announceChoice = sizerHelper.addLabeledControl(
			# Translators: Label of the choice whether this item speaks its name when it runs.
			_("Announce the name when this item runs"),
			wx.Choice,
			choices=ANNOUNCE_LABELS,
		)
		self.announceChoice.SetSelection(0)

		# Translators: Checkbox that turns an item on or off without deleting it.
		self.enabledCheck = wx.CheckBox(self, wx.ID_ANY, _("Enabled"))
		self.enabledCheck.SetValue(True)
		sizerHelper.addItem(self.enabledCheck)

		self.restrictionRow, self.restrictToAppsCheck, self.appNameLabel, self.appNameCtrl = (
			self._createRestrictionRow()
		)
		sizerHelper.addItem(self.restrictionRow, flag=wx.EXPAND)

		self.shortcutRow, self.shortcutLabel, self.shortcutButton, _unused = _labeledRow(
			self,
			# Translators: Label of the button that sets the item's shortcut.
			_("Shortcut"),
			lambda: wx.Button(self, wx.ID_ANY, ""),
			proportion=0,
		)
		sizerHelper.addItem(self.shortcutRow, flag=wx.EXPAND)

		buttonSizer = guiHelper.ButtonHelper(wx.HORIZONTAL)
		# Translators: OK button of the item dialog.
		self.okButton = buttonSizer.addButton(self, wx.ID_OK, _("&OK"))
		# Translators: Cancel button of the item dialog.
		buttonSizer.addButton(self, wx.ID_CANCEL, _("&Cancel"))

		mainSizer.Add(sizerHelper.sizer, 1, wx.ALL | wx.EXPAND, 10)
		mainSizer.Add(buttonSizer.sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)
		self.SetSizerAndFit(mainSizer)
		self.SetMinSize((700, 560))

		self.addActionButton.Bind(wx.EVT_BUTTON, self.onAddAction)
		self.editActionButton.Bind(wx.EVT_BUTTON, self.onEditAction)
		self.deleteActionButton.Bind(wx.EVT_BUTTON, self.onDeleteAction)
		self.moveUpActionButton.Bind(wx.EVT_BUTTON, self.onMoveActionUp)
		self.moveDownActionButton.Bind(wx.EVT_BUTTON, self.onMoveActionDown)
		self.actionsList.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onActionsSelectionChanged)
		self.actionsList.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.onActionsSelectionChanged)
		self.actionsList.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.onEditAction)
		self.actionsList.Bind(wx.EVT_KEY_DOWN, self.onActionsListKeyDown)
		self.shortcutButton.Bind(wx.EVT_BUTTON, self.onSetShortcut)
		self.restrictToAppsCheck.Bind(wx.EVT_CHECKBOX, self.onRestrictionToggle)
		self.okButton.Bind(wx.EVT_BUTTON, self.onOk)
		self.Bind(wx.EVT_CHAR_HOOK, self.onCharHook)

		if existingItem:
			self._loadExistingItem(existingItem)

		self.updateShortcutLabel()
		self.updateRestrictionState()
		self.refreshActionsList()
		self.CentreOnScreen()

	def _createRestrictionRow(self):
		row = wx.BoxSizer(wx.HORIZONTAL)
		# Translators: Checkbox that limits the item to the apps named in the next field.
		check = wx.CheckBox(self, wx.ID_ANY, _("Restrict this shortcut to work in certain apps"))
		# Translators: Label of the field for the apps the item is limited to.
		appLabel = wx.StaticText(self, wx.ID_ANY, _("App names, separated by commas"))
		appCtrl = wx.TextCtrl(self, wx.ID_ANY)
		# Translators: Hint shown inside the empty app names field.
		appCtrl.SetHint(_("notepad, winword"))
		row.Add(check, 0, wx.ALIGN_CENTER_VERTICAL)
		row.Add(
			appLabel,
			0,
			wx.ALIGN_CENTER_VERTICAL | wx.LEFT,
			guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL,
		)
		row.Add(appCtrl, 1, wx.LEFT, guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		return row, check, appLabel, appCtrl

	def _loadExistingItem(self, item):
		self.nameCtrl.SetValue(item.get("name", ""))
		gestures = item.get("gestures", [])
		if gestures:
			self.gesture = normalizeGesture(gestures[0])
		self.actions = [dict(action) for action in item.get("actions", [])]
		self.intervalCtrl.SetValue(_formatDelay(item.get("interval", 0.0)))
		self.stopOnErrorCheck.SetValue(bool(item.get("stopOnError", True)))
		self.announceChoice.SetSelection(ANNOUNCE_VALUES.index(item.get("announceName", ANNOUNCE_VALUES[0])))
		self.enabledCheck.SetValue(bool(item.get("enabled", True)))
		appName = (item.get("appName", "") or "").strip()
		if appName:
			self.restrictToAppsCheck.SetValue(True)
			self.appNameCtrl.SetValue(appName)

	def onCharHook(self, event):
		if event.GetKeyCode() == wx.WXK_ESCAPE:
			self.EndModal(wx.ID_CANCEL)
			return
		event.Skip()

	def updateShortcutLabel(self):
		if self.gesture:
			# Translators: Label of the shortcut button. {gesture} is the shortcut, for example g.
			label = _("Shortcut key: {gesture}").format(gesture=gestureDisplayText(self.gesture))
		else:
			# Translators: Label of the shortcut button when no shortcut is set.
			label = _("Shortcut key: Undefined")
		self.shortcutButton.SetLabel(label)

	def updateRestrictionState(self):
		isRestricted = self.restrictToAppsCheck.GetValue()
		self.appNameLabel.Show(isRestricted)
		self.appNameCtrl.Show(isRestricted)
		self.Layout()

	def onRestrictionToggle(self, event):
		isEmpty = not self.appNameCtrl.GetValue().strip()
		if self.restrictToAppsCheck.GetValue() and isEmpty and self.getPreviousAppName:
			self.appNameCtrl.SetValue(self.getPreviousAppName())
		self.updateRestrictionState()

	def getSelectedActionIndex(self):
		return self.actionsList.GetFirstSelected()

	def refreshActionsList(self, selectIndex=-1):
		self.actionsList.DeleteAllItems()
		for index, action in enumerate(self.actions):
			typeLabel, delayText, details = _getActionSummary(action)
			self.actionsList.InsertItem(index, typeLabel)
			self.actionsList.SetItem(index, 1, delayText)
			self.actionsList.SetItem(index, 2, details)
		if 0 <= selectIndex < len(self.actions):
			self.actionsList.Select(selectIndex)
			self.actionsList.Focus(selectIndex)
		self.updateActionButtons()

	def updateActionButtons(self):
		index = self.getSelectedActionIndex()
		hasSelection = index != -1
		self.editActionButton.Enable(hasSelection)
		self.deleteActionButton.Enable(hasSelection)
		self.moveUpActionButton.Enable(hasSelection and index > 0)
		self.moveDownActionButton.Enable(hasSelection and index != -1 and index < len(self.actions) - 1)

	def onActionsSelectionChanged(self, event):
		self.updateActionButtons()

	def onAddAction(self, event):
		# Translators: Title of the dialog that adds an action.
		dialog = InstantAccessActionDialog(self, _("Add action"))
		if dialog.ShowModal() == wx.ID_OK:
			self.actions.append(dialog.result)
			self.refreshActionsList(selectIndex=len(self.actions) - 1)
		dialog.Destroy()
		self.actionsList.SetFocus()

	def onEditAction(self, event):
		index = self.getSelectedActionIndex()
		if index == -1:
			return
		# Translators: Title of the dialog that edits an action.
		dialog = InstantAccessActionDialog(self, _("Edit action"), existingAction=self.actions[index])
		if dialog.ShowModal() == wx.ID_OK:
			self.actions[index] = dialog.result
			self.refreshActionsList(selectIndex=index)
		dialog.Destroy()
		self.actionsList.SetFocus()

	def onDeleteAction(self, event):
		index = self.getSelectedActionIndex()
		if index == -1:
			return
		if (
			gui.messageBox(
				# Translators: Question before deleting an action.
				_("Are you sure you would like to delete the selected action?"),
				# Translators: Title of the question before deleting an action.
				_("Confirm"),
				wx.YES_NO | wx.ICON_QUESTION,
			)
			!= wx.YES
		):
			return
		del self.actions[index]
		nextIndex = min(index, len(self.actions) - 1)
		self.refreshActionsList(selectIndex=nextIndex)
		self.actionsList.SetFocus()

	def _moveAction(self, step):
		index = self.getSelectedActionIndex()
		target = index + step
		if index == -1 or not 0 <= target < len(self.actions):
			return
		self.actions[index], self.actions[target] = self.actions[target], self.actions[index]
		self.refreshActionsList(selectIndex=target)
		self.actionsList.SetFocus()

	def onMoveActionUp(self, event):
		self._moveAction(-1)

	def onMoveActionDown(self, event):
		self._moveAction(1)

	def onActionsListKeyDown(self, event):
		keyCode = event.GetKeyCode()
		if keyCode == wx.WXK_DELETE:
			self.onDeleteAction(event)
			return
		if event.ControlDown() and keyCode == wx.WXK_UP:
			self.onMoveActionUp(event)
			return
		if event.ControlDown() and keyCode == wx.WXK_DOWN:
			self.onMoveActionDown(event)
			return
		event.Skip()

	def getReservedGestures(self):
		reserved = {gestureKey(gesture) for gesture in RESERVED_GESTURES}
		for description, fallback in ADDON_SCRIPT_GESTURES.items():
			reserved.update(gestureKey(gesture) for gesture in getAddonGestures(description, fallback))
		return reserved

	def onSetShortcut(self, event):
		dialog = ShortcutCaptureDialog(self)
		if dialog.ShowModal() == wx.ID_OK:
			gestureName = normalizeGesture(dialog.gestureName)
			if not gestureName:
				dialog.Destroy()
				return
			if gestureKey(gestureName) in self.getReservedGestures():
				gui.messageBox(
					# Translators: Error shown when the captured shortcut is one of the add-on's own commands.
					_("This shortcut is reserved for instant Access."),
					ERROR_CAPTION,
					wx.OK | wx.ICON_ERROR,
				)
				dialog.Destroy()
				return
			if not validateGestureName(formatGestureForDisplay(gestureName)):
				# Translators: Error shown when the captured key is not a valid NVDA gesture.
				gui.messageBox(_("Invalid shortcut key."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
				dialog.Destroy()
				return
			self.gesture = gestureName
			self.updateShortcutLabel()
		dialog.Destroy()

	def validate(self):
		name = self.nameCtrl.GetValue().strip()
		gesture = self.gesture
		appName = ", ".join(parseAppNames(self.appNameCtrl.GetValue())) if self.restrictToAppsCheck.GetValue() else ""

		if not name or not gesture:
			# Translators: Error shown when the item has no name or no shortcut.
			gui.messageBox(_("All fields are required."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None
		if not self.actions:
			# Translators: Error shown when the item has no actions.
			gui.messageBox(_("At least one action is required."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None
		if self.restrictToAppsCheck.GetValue() and not appName:
			gui.messageBox(
				# Translators: Error shown when app restriction is on but the app name is empty.
				_("App name is required when app restriction is enabled."),
				ERROR_CAPTION,
				wx.OK | wx.ICON_ERROR,
			)
			return None

		interval = parseDelayField(
			self.intervalCtrl.GetValue(),
			# Translators: Error shown when the interval between actions is not a number.
			_("Interval must be a valid number."),
			# Translators: Error shown when the interval between actions is negative.
			_("Interval must be zero or greater."),
		)
		if interval is None:
			return None

		normalizedGesture = normalizeGesture(gesture)
		if gestureKey(normalizedGesture) in self.getReservedGestures():
			gui.messageBox(
				# Translators: Error shown when the item's shortcut is one of the add-on's own commands.
				_("This shortcut is reserved for instant Access."),
				ERROR_CAPTION,
				wx.OK | wx.ICON_ERROR,
			)
			return None
		if not validateGestureName(formatGestureForDisplay(normalizedGesture)):
			# Translators: Error shown when the item's shortcut is not a valid NVDA gesture.
			gui.messageBox(_("Invalid shortcut key."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None

		allNames = self.configManager.getAllNames()
		if self.existingItem:
			allNames.discard(self.existingItem["name"])
		if name in allNames:
			# Translators: Error shown when another item has the same name.
			gui.messageBox(_("This name already exists."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None

		excludeName = self.existingItem["name"] if self.existingItem else ""
		conflictItem = self.configManager.findGestureConflict(
			normalizedGesture,
			appName=appName,
			excludeName=excludeName,
		)
		if conflictItem:
			conflictName = conflictItem.get("name", "")
			if appName:
				# Translators: Error shown when an app-specific shortcut conflicts with an existing item.
				msg = _("This shortcut is already assigned to '{name}' for this app.").format(
					name=conflictName,
				)
			else:
				# Translators: Error shown when a global shortcut conflicts with an existing item.
				msg = _("This global shortcut is already assigned to '{name}'.").format(name=conflictName)
			gui.messageBox(msg, ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None

		return {
			"name": name,
			"gesture": normalizedGesture,
			"appName": appName,
			"interval": interval,
			"stopOnError": self.stopOnErrorCheck.GetValue(),
			"enabled": self.enabledCheck.GetValue(),
			"announceName": ANNOUNCE_VALUES[self.announceChoice.GetSelection()],
			"actions": [dict(action) for action in self.actions],
		}

	def onOk(self, event):
		result = self.validate()
		if not result:
			return
		self.result = result
		self.EndModal(wx.ID_OK)
