# -*- coding: utf-8 -*-

import gui
from gui import guiHelper, nvdaControls
import wx

from .command_picker_dialog import NvdaCommandPickerDialog
from .constants import (
	ALL_FILES_WILDCARD,
	ERROR_CAPTION,
	RESERVED_GESTURES,
	TEXT_SNIPPET_ACTION_LABELS,
	TEXT_SNIPPET_ACTION_TO_LABEL,
	TEXT_SNIPPET_ACTION_VALUES,
	TYPE_LABELS,
	TYPE_SECTIONS,
	TYPE_TO_LABEL,
)
from .gestures import buildGestureNameFromEvent, formatGestureForDisplay, normalizeGesture, validateGestureName


def _formatDelay(delayValue):
	try:
		number = float(delayValue)
	except Exception:
		number = 0.0
	if number < 0:
		number = 0.0
	formatted = f"{number:.3f}".rstrip("0").rstrip(".")
	return formatted or "0"


def _getActionSummary(action):
	itemType = action.get("type", "")
	typeLabel = TYPE_TO_LABEL.get(itemType, itemType).replace("&", "")
	delayText = _formatDelay(action.get("delay", 0.0))
	if itemType == "TextSnippets":
		text = (action.get("path", "") or "").replace("\r\n", "\n").replace("\r", "\n")
		firstLine = text.split("\n", 1)[0]
		if len(firstLine) > 50:
			firstLine = firstLine[:47] + "..."
		details = _("{action}: {preview}").format(
			action=TEXT_SNIPPET_ACTION_TO_LABEL.get(action.get("textAction", "type"), TEXT_SNIPPET_ACTION_TO_LABEL["type"]),
			preview=firstLine,
		)
	elif itemType == "NvdaCommands":
		details = action.get("commandLabel", "") or action.get("path", "")
	else:
		details = action.get("path", "")
		if itemType == "Programs" and action.get("arguments", "").strip():
			details = f"{details} {action.get('arguments', '').strip()}"
	return typeLabel, delayText, details


class ShortcutCaptureDialog(wx.Dialog):
	def __init__(self, parent):
		wx.Dialog.__init__(self, parent, title=_("Set shortcut"), style=wx.DEFAULT_DIALOG_STYLE)
		self.gestureName = ""
		mainSizer = wx.BoxSizer(wx.VERTICAL)
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

		mainSizer = wx.BoxSizer(wx.VERTICAL)
		sizerHelper = guiHelper.BoxSizerHelper(self, wx.VERTICAL)

		self.typeChoice = sizerHelper.addLabeledControl(_("Type"), wx.Choice, choices=TYPE_LABELS)
		self.typeChoice.SetSelection(0)

		self.pathRow, self.pathCtrl, self.browseButton = self._createPathRow()
		sizerHelper.addItem(self.pathRow, flag=wx.EXPAND)

		self.argumentsRow, self.argumentsCtrl = self._createArgumentsRow()
		sizerHelper.addItem(self.argumentsRow, flag=wx.EXPAND)

		self.commandRow, self.commandCtrl, self.commandButton = self._createCommandRow()
		sizerHelper.addItem(self.commandRow, flag=wx.EXPAND)

		self.snippetRow, self.snippetCtrl = self._createSnippetRow()
		sizerHelper.addItem(self.snippetRow, flag=wx.EXPAND)

		self.snippetActionRow, self.snippetActionChoice = self._createSnippetActionRow()
		sizerHelper.addItem(self.snippetActionRow, flag=wx.EXPAND)
		self.typingDelayRow, self.typingDelayCtrl = self._createTypingDelayRow()
		sizerHelper.addItem(self.typingDelayRow, flag=wx.EXPAND)
		self.typingDelayCtrl.SetValue("0.05")

		self.delayCtrl = sizerHelper.addLabeledControl(_("Delay before executing this action"), wx.TextCtrl)
		self.delayCtrl.SetValue("0")

		buttonSizer = guiHelper.ButtonHelper(wx.HORIZONTAL)
		self.okButton = buttonSizer.addButton(self, wx.ID_OK, _("&OK"))
		buttonSizer.addButton(self, wx.ID_CANCEL, _("&Cancel"))

		mainSizer.Add(sizerHelper.sizer, 1, wx.ALL | wx.EXPAND, 10)
		mainSizer.Add(buttonSizer.sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)
		self.SetSizerAndFit(mainSizer)
		self.SetMinSize((560, 460))

		self.typeChoice.Bind(wx.EVT_CHOICE, self.onTypeChange)
		self.snippetActionChoice.Bind(wx.EVT_CHOICE, self.onSnippetActionChange)
		self.browseButton.Bind(wx.EVT_BUTTON, self.onBrowse)
		self.commandButton.Bind(wx.EVT_BUTTON, self.onSelectCommand)
		self.okButton.Bind(wx.EVT_BUTTON, self.onOk)

		if existingAction:
			self._loadExistingAction(existingAction)

		self.updateTypeState()
		self.CentreOnScreen()

	def _createPathRow(self):
		row = wx.BoxSizer(wx.HORIZONTAL)
		label = wx.StaticText(self, wx.ID_ANY, _("Path or URL"))
		ctrl = wx.TextCtrl(self, wx.ID_ANY)
		button = wx.Button(self, wx.ID_ANY, _("Browse"))
		row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		row.Add(ctrl, 1, wx.RIGHT, guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		row.Add(button, 0)
		return row, ctrl, button

	def _createArgumentsRow(self):
		row = wx.BoxSizer(wx.HORIZONTAL)
		label = wx.StaticText(self, wx.ID_ANY, _("Arguments (optional)"))
		ctrl = wx.TextCtrl(self, wx.ID_ANY)
		row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		row.Add(ctrl, 1)
		return row, ctrl

	def _createCommandRow(self):
		row = wx.BoxSizer(wx.HORIZONTAL)
		label = wx.StaticText(self, wx.ID_ANY, _("NVDA command"))
		ctrl = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY)
		button = wx.Button(self, wx.ID_ANY, _("Select command"))
		row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		row.Add(ctrl, 1, wx.RIGHT, guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		row.Add(button, 0)
		return row, ctrl, button

	def _createSnippetRow(self):
		row = wx.BoxSizer(wx.HORIZONTAL)
		label = wx.StaticText(self, wx.ID_ANY, _("Text snippet"))
		ctrl = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_MULTILINE, size=(-1, 120))
		row.Add(label, 0, wx.ALIGN_TOP | wx.RIGHT, guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		row.Add(ctrl, 1, wx.EXPAND)
		return row, ctrl

	def _createSnippetActionRow(self):
		row = wx.BoxSizer(wx.HORIZONTAL)
		label = wx.StaticText(self, wx.ID_ANY, _("Snippet action"))
		choice = wx.Choice(self, wx.ID_ANY, choices=TEXT_SNIPPET_ACTION_LABELS)
		choice.SetSelection(0)
		row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		row.Add(choice, 0)
		return row, choice

	def _createTypingDelayRow(self):
		row = wx.BoxSizer(wx.HORIZONTAL)
		label = wx.StaticText(self, wx.ID_ANY, _("Typing delay"))
		ctrl = wx.TextCtrl(self, wx.ID_ANY)
		row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		row.Add(ctrl, 0)
		return row, ctrl

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
		self.selectedCommandId = action.get("path", "") if itemType == "NvdaCommands" else ""
		self.selectedCommandLabel = action.get("commandLabel", "")
		if self.selectedCommandLabel:
			self.commandCtrl.SetValue(self.selectedCommandLabel)
		self.snippetCtrl.SetValue(action.get("path", "") if itemType == "TextSnippets" else "")
		actionValue = (action.get("textAction", TEXT_SNIPPET_ACTION_VALUES[0]) or "").strip().lower()
		if actionValue in TEXT_SNIPPET_ACTION_VALUES:
			self.snippetActionChoice.SetSelection(TEXT_SNIPPET_ACTION_VALUES.index(actionValue))
		self.typingDelayCtrl.SetValue(_formatDelay(action.get("typingDelay", 0.05)))
		self.delayCtrl.SetValue(_formatDelay(action.get("delay", 0.0)))

	def updateTypeState(self):
		itemType = TYPE_SECTIONS[self.typeChoice.GetSelection()]
		showPath = itemType in ("Websites", "Programs", "Folders", "Files")
		showArguments = itemType == "Programs"
		showCommand = itemType == "NvdaCommands"
		showSnippet = itemType == "TextSnippets"
		showTypingDelay = showSnippet and TEXT_SNIPPET_ACTION_VALUES[self.snippetActionChoice.GetSelection()] == "type"

		self._setRowVisible(self.pathRow, showPath)
		self._setRowVisible(self.argumentsRow, showArguments)
		self._setRowVisible(self.commandRow, showCommand)
		self._setRowVisible(self.snippetRow, showSnippet)
		self._setRowVisible(self.snippetActionRow, showSnippet)
		self._setRowVisible(self.typingDelayRow, showTypingDelay)
		self.browseButton.Enable(itemType in ("Programs", "Folders", "Files"))
		self.Layout()

	def onTypeChange(self, event):
		self.updateTypeState()

	def onSnippetActionChange(self, event):
		self.updateTypeState()

	def onBrowse(self, event):
		itemType = TYPE_SECTIONS[self.typeChoice.GetSelection()]
		if itemType == "Programs":
			dialog = wx.FileDialog(self, _("Select a program"), wildcard=ALL_FILES_WILDCARD, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
			if dialog.ShowModal() == wx.ID_OK:
				self.pathCtrl.SetValue(dialog.GetPath())
			dialog.Destroy()
			return
		if itemType == "Folders":
			dialog = wx.DirDialog(self, _("Select a folder"), style=wx.DD_DIR_MUST_EXIST)
			if dialog.ShowModal() == wx.ID_OK:
				self.pathCtrl.SetValue(dialog.GetPath())
			dialog.Destroy()
			return
		if itemType == "Files":
			dialog = wx.FileDialog(self, _("Select a file"), wildcard=ALL_FILES_WILDCARD, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
			if dialog.ShowModal() == wx.ID_OK:
				self.pathCtrl.SetValue(dialog.GetPath())
			dialog.Destroy()

	def onSelectCommand(self, event):
		dialog = NvdaCommandPickerDialog(self, selectedCommandId=self.selectedCommandId)
		if dialog.ShowModal() == wx.ID_OK:
			self.selectedCommandId = dialog.result["commandId"]
			self.selectedCommandLabel = dialog.result["commandLabel"]
			self.commandCtrl.SetValue(self.selectedCommandLabel)
		dialog.Destroy()

	def validate(self):
		itemType = TYPE_SECTIONS[self.typeChoice.GetSelection()]
		arguments = self.argumentsCtrl.GetValue().strip() if itemType == "Programs" else ""
		textAction = TEXT_SNIPPET_ACTION_VALUES[self.snippetActionChoice.GetSelection()]

		if itemType == "TextSnippets":
			path = self.snippetCtrl.GetValue()
		elif itemType == "NvdaCommands":
			path = self.selectedCommandId.strip()
		else:
			path = self.pathCtrl.GetValue().strip()

		if itemType == "TextSnippets":
			if not path.strip():
				gui.messageBox(_("All fields are required."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
				return None
		elif not path:
			gui.messageBox(_("All fields are required."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None

		try:
			delay = float((self.delayCtrl.GetValue() or "0").strip())
		except Exception:
			gui.messageBox(_("Delay must be a valid number."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None
		if delay < 0:
			gui.messageBox(_("Delay must be zero or greater."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None

		typingDelay = 0.05
		if itemType == "TextSnippets" and textAction == "type":
			try:
				typingDelay = float((self.typingDelayCtrl.GetValue() or "0.05").strip())
			except Exception:
				gui.messageBox(_("Typing delay must be a valid number."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
				return None
			if typingDelay < 0:
				gui.messageBox(_("Typing delay must be zero or greater."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
				return None

		return {
			"type": itemType,
			"path": path,
			"arguments": arguments,
			"textAction": textAction,
			"typingDelay": typingDelay,
			"commandLabel": self.selectedCommandLabel.strip(),
			"delay": delay,
		}

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
		self.existingItem = existingItem
		self.gesture = ""
		self.actions = []

		mainSizer = wx.BoxSizer(wx.VERTICAL)
		sizerHelper = guiHelper.BoxSizerHelper(self, wx.VERTICAL)

		self.nameCtrl = sizerHelper.addLabeledControl(_("Name"), wx.TextCtrl)

		actionsLabel = wx.StaticText(self, wx.ID_ANY, _("Actions"))
		sizerHelper.addItem(actionsLabel)
		self.actionsList = nvdaControls.AutoWidthColumnListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN)
		self.actionsList.InsertColumn(0, _("Type"))
		self.actionsList.InsertColumn(1, _("Delay"))
		self.actionsList.InsertColumn(2, _("Details"))
		sizerHelper.addItem(self.actionsList, flag=wx.EXPAND, proportion=1)

		actionsButtons = guiHelper.ButtonHelper(wx.HORIZONTAL)
		self.addActionButton = actionsButtons.addButton(self, label=_("&Add"))
		self.editActionButton = actionsButtons.addButton(self, label=_("&Edit"))
		self.deleteActionButton = actionsButtons.addButton(self, label=_("&Delete"))
		self.moveUpActionButton = actionsButtons.addButton(self, label=_("Move &up"))
		self.moveDownActionButton = actionsButtons.addButton(self, label=_("Move &down"))
		sizerHelper.addItem(actionsButtons.sizer, flag=wx.EXPAND)

		self.intervalCtrl = sizerHelper.addLabeledControl(_("Interval between actions (seconds)"), wx.TextCtrl)
		self.intervalCtrl.SetValue("0")

		self.restrictionRow, self.restrictToAppsCheck, self.appNameLabel, self.appNameCtrl = self._createRestrictionRow()
		sizerHelper.addItem(self.restrictionRow, flag=wx.EXPAND)

		self.shortcutRow, self.shortcutButton = self._createShortcutRow()
		sizerHelper.addItem(self.shortcutRow, flag=wx.EXPAND)

		buttonSizer = guiHelper.ButtonHelper(wx.HORIZONTAL)
		self.okButton = buttonSizer.addButton(self, wx.ID_OK, _("&OK"))
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
		check = wx.CheckBox(self, wx.ID_ANY, _("Restrict this shortcut to work in certain apps"))
		appLabel = wx.StaticText(self, wx.ID_ANY, _("App name"))
		appCtrl = wx.TextCtrl(self, wx.ID_ANY)
		appCtrl.SetHint(_("App name"))
		row.Add(check, 0, wx.ALIGN_CENTER_VERTICAL)
		row.Add(appLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		row.Add(appCtrl, 1, wx.LEFT, guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		return row, check, appLabel, appCtrl

	def _createShortcutRow(self):
		row = wx.BoxSizer(wx.HORIZONTAL)
		label = wx.StaticText(self, wx.ID_ANY, _("Shortcut"))
		button = wx.Button(self, wx.ID_ANY, "")
		row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		row.Add(button, 0)
		return row, button

	def _loadExistingItem(self, item):
		self.nameCtrl.SetValue(item.get("name", ""))
		gestures = item.get("gestures", [])
		if gestures:
			self.gesture = normalizeGesture(gestures[0])
		self.actions = [dict(action) for action in item.get("actions", [])]
		self.intervalCtrl.SetValue(_formatDelay(item.get("interval", 0.0)))
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
			label = _("Shortcut key: {gesture}").format(gesture=formatGestureForDisplay(self.gesture))
		else:
			label = _("Shortcut key: Undefined")
		self.shortcutButton.SetLabel(label)

	def updateRestrictionState(self):
		isRestricted = self.restrictToAppsCheck.GetValue()
		self.appNameLabel.Show(isRestricted)
		self.appNameCtrl.Show(isRestricted)
		self.Layout()

	def onRestrictionToggle(self, event):
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
		if gui.messageBox(_("Are you sure you would like to delete the selected action?"), _("Confirm"), wx.YES_NO | wx.ICON_QUESTION) != wx.YES:
			return
		del self.actions[index]
		nextIndex = min(index, len(self.actions) - 1)
		self.refreshActionsList(selectIndex=nextIndex)
		self.actionsList.SetFocus()

	def onMoveActionUp(self, event):
		index = self.getSelectedActionIndex()
		if index <= 0:
			return
		self.actions[index - 1], self.actions[index] = self.actions[index], self.actions[index - 1]
		self.refreshActionsList(selectIndex=index - 1)
		self.actionsList.SetFocus()

	def onMoveActionDown(self, event):
		index = self.getSelectedActionIndex()
		if index == -1 or index >= len(self.actions) - 1:
			return
		self.actions[index + 1], self.actions[index] = self.actions[index], self.actions[index + 1]
		self.refreshActionsList(selectIndex=index + 1)
		self.actionsList.SetFocus()

	def onSetShortcut(self, event):
		dialog = ShortcutCaptureDialog(self)
		if dialog.ShowModal() == wx.ID_OK:
			gestureName = normalizeGesture(dialog.gestureName)
			if not gestureName:
				dialog.Destroy()
				return
			if gestureName in RESERVED_GESTURES:
				gui.messageBox(_("This shortcut is reserved for instant Access."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
				dialog.Destroy()
				return
			if not validateGestureName(formatGestureForDisplay(gestureName)):
				gui.messageBox(_("Invalid shortcut key."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
				dialog.Destroy()
				return
			self.gesture = gestureName
			self.updateShortcutLabel()
		dialog.Destroy()

	def validate(self):
		name = self.nameCtrl.GetValue().strip()
		gesture = self.gesture
		appName = self.appNameCtrl.GetValue().strip().lower() if self.restrictToAppsCheck.GetValue() else ""

		if not name or not gesture:
			gui.messageBox(_("All fields are required."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None
		if not self.actions:
			gui.messageBox(_("At least one action is required."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None
		if self.restrictToAppsCheck.GetValue() and not appName:
			gui.messageBox(_("App name is required when app restriction is enabled."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None

		try:
			interval = float((self.intervalCtrl.GetValue() or "0").strip())
		except Exception:
			gui.messageBox(_("Interval must be a valid number."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None
		if interval < 0:
			gui.messageBox(_("Interval must be zero or greater."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None

		normalizedGesture = normalizeGesture(gesture)
		if normalizedGesture in RESERVED_GESTURES:
			gui.messageBox(_("This shortcut is reserved for instant Access."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None
		if not validateGestureName(formatGestureForDisplay(normalizedGesture)):
			gui.messageBox(_("Invalid shortcut key."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None

		allNames = self.configManager.getAllNames()
		if self.existingItem:
			allNames.discard(self.existingItem["name"])
		if name in allNames:
			gui.messageBox(_("This name already exists."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None

		excludeName = self.existingItem["name"] if self.existingItem else ""
		conflictItem = self.configManager.findGestureConflict(normalizedGesture, appName=appName, excludeName=excludeName)
		if conflictItem:
			if appName:
				gui.messageBox(_("This shortcut is already assigned for this app."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			else:
				gui.messageBox(_("This global shortcut is already assigned."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None

		return {
			"name": name,
			"gesture": normalizedGesture,
			"appName": appName,
			"interval": interval,
			"actions": [dict(action) for action in self.actions],
		}

	def onOk(self, event):
		result = self.validate()
		if not result:
			return
		self.result = result
		self.EndModal(wx.ID_OK)
