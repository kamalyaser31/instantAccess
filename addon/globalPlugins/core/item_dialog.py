# -*- coding: utf-8 -*-

import gui
from gui import guiHelper
import wx

from .command_picker_dialog import NvdaCommandPickerDialog
from .constants import (
	ALL_FILES_WILDCARD,
	ERROR_CAPTION,
	RESERVED_GESTURES,
	TEXT_SNIPPET_ACTION_LABELS,
	TEXT_SNIPPET_ACTION_VALUES,
	TYPE_LABELS,
	TYPE_SECTIONS,
)
from .gestures import buildGestureNameFromEvent, formatGestureForDisplay, normalizeGesture, validateGestureName


class ShortcutCaptureDialog(wx.Dialog):
	def __init__(self, parent):
		# Translators: Title of the dialog used to capture a shortcut key.
		wx.Dialog.__init__(self, parent, title=_("Set shortcut"), style=wx.DEFAULT_DIALOG_STYLE)
		self.gestureName = ""
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		# Translators: Instructions in the shortcut capture dialog.
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


class InstantAccessItemDialog(wx.Dialog):
	def __init__(self, parent, configManager, title, existingItem=None):
		wx.Dialog.__init__(self, parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
		self.configManager = configManager
		self.existingItem = existingItem
		self.gesture = ""
		self.selectedCommandId = ""
		self.selectedCommandLabel = ""

		mainSizer = wx.BoxSizer(wx.VERTICAL)
		sizerHelper = guiHelper.BoxSizerHelper(self, wx.VERTICAL)

		# Translators: Label for the name field in the add/edit dialog.
		self.nameCtrl = sizerHelper.addLabeledControl(_("Name"), wx.TextCtrl)
		# Translators: Label for the type field in the add/edit dialog.
		self.typeChoice = sizerHelper.addLabeledControl(_("Type"), wx.Choice, choices=TYPE_LABELS)
		self.typeChoice.SetSelection(0)

		self.pathRow, self.pathLabel, self.pathCtrl, self.browseButton = self._createPathRow()
		sizerHelper.addItem(self.pathRow, flag=wx.EXPAND)

		self.argumentsRow, self.argumentsCtrl = self._createArgumentsRow()
		sizerHelper.addItem(self.argumentsRow, flag=wx.EXPAND)

		self.commandRow, self.commandCtrl, self.commandButton = self._createCommandRow()
		sizerHelper.addItem(self.commandRow, flag=wx.EXPAND)

		self.snippetRow, self.snippetCtrl = self._createSnippetRow()
		sizerHelper.addItem(self.snippetRow, flag=wx.EXPAND)

		self.snippetActionRow, self.snippetActionChoice = self._createSnippetActionRow()
		sizerHelper.addItem(self.snippetActionRow, flag=wx.EXPAND)

		self.shortcutRow, self.shortcutButton = self._createShortcutRow()
		sizerHelper.addItem(self.shortcutRow, flag=wx.EXPAND)

		buttonSizer = guiHelper.ButtonHelper(wx.HORIZONTAL)
		# Translators: Label for the OK button in the add/edit dialog.
		self.okButton = buttonSizer.addButton(self, wx.ID_OK, _("&OK"))
		# Translators: Label for the Cancel button in the add/edit dialog.
		buttonSizer.addButton(self, wx.ID_CANCEL, _("&Cancel"))

		mainSizer.Add(sizerHelper.sizer, 1, wx.ALL | wx.EXPAND, 10)
		mainSizer.Add(buttonSizer.sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)
		self.SetSizerAndFit(mainSizer)
		self.SetMinSize((560, 520))

		self.Bind(wx.EVT_CHOICE, self.onTypeChange, self.typeChoice)
		self.Bind(wx.EVT_BUTTON, self.onBrowse, self.browseButton)
		self.Bind(wx.EVT_BUTTON, self.onSetShortcut, self.shortcutButton)
		self.Bind(wx.EVT_BUTTON, self.onSelectCommand, self.commandButton)
		self.Bind(wx.EVT_BUTTON, self.onOk, self.okButton)
		self.Bind(wx.EVT_CHAR_HOOK, self.onCharHook)

		if existingItem:
			self._loadExistingItem(existingItem)

		self.updateShortcutLabel()
		self.updateTypeState()
		self.CentreOnScreen()

	def _createPathRow(self):
		row = wx.BoxSizer(wx.HORIZONTAL)
		# Translators: Label for the path or URL field in the add/edit dialog.
		label = wx.StaticText(self, wx.ID_ANY, _("Path or URL"))
		ctrl = wx.TextCtrl(self, wx.ID_ANY)
		# Translators: Label for the browse button in the add/edit dialog.
		button = wx.Button(self, wx.ID_ANY, _("Browse"))
		row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		row.Add(ctrl, 1, wx.RIGHT, guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		row.Add(button, 0)
		return row, label, ctrl, button

	def _createArgumentsRow(self):
		row = wx.BoxSizer(wx.HORIZONTAL)
		# Translators: Label for optional command line arguments in the add/edit dialog.
		label = wx.StaticText(self, wx.ID_ANY, _("Arguments (optional)"))
		ctrl = wx.TextCtrl(self, wx.ID_ANY)
		row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		row.Add(ctrl, 1)
		return row, ctrl

	def _createCommandRow(self):
		row = wx.BoxSizer(wx.HORIZONTAL)
		# Translators: Label for selected NVDA command.
		label = wx.StaticText(self, wx.ID_ANY, _("NVDA command"))
		ctrl = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY)
		# Translators: Label for button opening NVDA command picker.
		button = wx.Button(self, wx.ID_ANY, _("Select command"))
		row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		row.Add(ctrl, 1, wx.RIGHT, guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		row.Add(button, 0)
		return row, ctrl, button

	def _createSnippetRow(self):
		row = wx.BoxSizer(wx.HORIZONTAL)
		# Translators: Label for text snippet field.
		label = wx.StaticText(self, wx.ID_ANY, _("Text snippet"))
		ctrl = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_MULTILINE, size=(-1, 120))
		row.Add(label, 0, wx.ALIGN_TOP | wx.RIGHT, guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		row.Add(ctrl, 1, wx.EXPAND)
		return row, ctrl

	def _createSnippetActionRow(self):
		row = wx.BoxSizer(wx.HORIZONTAL)
		# Translators: Label for text snippet action selector.
		label = wx.StaticText(self, wx.ID_ANY, _("Snippet action"))
		choice = wx.Choice(self, wx.ID_ANY, choices=TEXT_SNIPPET_ACTION_LABELS)
		choice.SetSelection(0)
		row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		row.Add(choice, 0)
		return row, choice

	def _createShortcutRow(self):
		row = wx.BoxSizer(wx.HORIZONTAL)
		# Translators: Label for the shortcut section in the add/edit dialog.
		label = wx.StaticText(self, wx.ID_ANY, _("Shortcut"))
		button = wx.Button(self, wx.ID_ANY, "")
		row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		row.Add(button, 0)
		return row, button

	def _setRowVisible(self, row, visible):
		for child in row.GetChildren():
			if child.IsWindow():
				child.GetWindow().Show(visible)

	def _loadExistingItem(self, item):
		self.nameCtrl.SetValue(item.get("name", ""))
		itemType = item.get("type", TYPE_SECTIONS[0])
		if itemType in TYPE_SECTIONS:
			self.typeChoice.SetSelection(TYPE_SECTIONS.index(itemType))

		gestures = item.get("gestures", [])
		if gestures:
			self.gesture = normalizeGesture(gestures[0])

		self.argumentsCtrl.SetValue(item.get("arguments", ""))
		self.pathCtrl.SetValue(item.get("path", ""))

		self.selectedCommandId = item.get("path", "") if itemType == "NvdaCommands" else ""
		self.selectedCommandLabel = item.get("commandLabel", "")
		if self.selectedCommandLabel:
			self.commandCtrl.SetValue(self.selectedCommandLabel)

		if itemType == "TextSnippets":
			self.snippetCtrl.SetValue(item.get("path", ""))
			action = (item.get("textAction", TEXT_SNIPPET_ACTION_VALUES[0]) or "").strip().lower()
			if action in TEXT_SNIPPET_ACTION_VALUES:
				self.snippetActionChoice.SetSelection(TEXT_SNIPPET_ACTION_VALUES.index(action))

	def updateShortcutLabel(self):
		if self.gesture:
			# Translators: Label for the shortcut button when a shortcut is set. {gesture} is the assigned key.
			label = _("Shortcut key: {gesture}").format(gesture=formatGestureForDisplay(self.gesture))
		else:
			# Translators: Label for the shortcut button when no shortcut is set.
			label = _("Shortcut key: Undefined")
		self.shortcutButton.SetLabel(label)

	def onCharHook(self, event):
		if event.GetKeyCode() == wx.WXK_ESCAPE:
			self.EndModal(wx.ID_CANCEL)
			return
		event.Skip()

	def updateTypeState(self):
		itemType = TYPE_SECTIONS[self.typeChoice.GetSelection()]
		showPath = itemType in ("Websites", "Programs", "Folders", "Files")
		showArguments = itemType == "Programs"
		showCommand = itemType == "NvdaCommands"
		showSnippet = itemType == "TextSnippets"

		self._setRowVisible(self.pathRow, showPath)
		self._setRowVisible(self.argumentsRow, showArguments)
		self._setRowVisible(self.commandRow, showCommand)
		self._setRowVisible(self.snippetRow, showSnippet)
		self._setRowVisible(self.snippetActionRow, showSnippet)

		self.browseButton.Enable(itemType in ("Programs", "Folders", "Files"))
		self.Layout()

	def onTypeChange(self, event):
		self.updateTypeState()

	def onBrowse(self, event):
		itemType = TYPE_SECTIONS[self.typeChoice.GetSelection()]
		if itemType == "Programs":
			dialog = wx.FileDialog(
				self,
				_("Select a program"),
				wildcard=ALL_FILES_WILDCARD,
				style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
			)
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
			dialog = wx.FileDialog(
				self,
				_("Select a file"),
				wildcard=ALL_FILES_WILDCARD,
				style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
			)
			if dialog.ShowModal() == wx.ID_OK:
				self.pathCtrl.SetValue(dialog.GetPath())
			dialog.Destroy()

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

	def onSelectCommand(self, event):
		dialog = NvdaCommandPickerDialog(self, selectedCommandId=self.selectedCommandId)
		if dialog.ShowModal() == wx.ID_OK:
			self.selectedCommandId = dialog.result["commandId"]
			self.selectedCommandLabel = dialog.result["commandLabel"]
			self.commandCtrl.SetValue(self.selectedCommandLabel)
		dialog.Destroy()

	def validate(self):
		name = self.nameCtrl.GetValue().strip()
		itemType = TYPE_SECTIONS[self.typeChoice.GetSelection()]
		gesture = self.gesture
		arguments = self.argumentsCtrl.GetValue().strip() if itemType == "Programs" else ""
		textAction = TEXT_SNIPPET_ACTION_VALUES[self.snippetActionChoice.GetSelection()]
		commandLabel = self.selectedCommandLabel.strip()

		if itemType == "TextSnippets":
			path = self.snippetCtrl.GetValue()
		elif itemType == "NvdaCommands":
			path = self.selectedCommandId.strip()
		else:
			path = self.pathCtrl.GetValue().strip()

		if not name or not gesture:
			gui.messageBox(_("All fields are required."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None
		if itemType == "TextSnippets" and not path.strip():
			gui.messageBox(_("All fields are required."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None
		if itemType != "TextSnippets" and not path:
			gui.messageBox(_("All fields are required."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
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

		gestureMap = self.configManager.getGestureToNameMap()
		existingName = gestureMap.get(normalizedGesture.lower())
		if existingName and (not self.existingItem or existingName != self.existingItem["name"]):
			gui.messageBox(_("This shortcut is already assigned."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None

		return {
			"name": name,
			"type": itemType,
			"path": path,
			"arguments": arguments,
			"textAction": textAction,
			"commandLabel": commandLabel,
			"gesture": normalizedGesture,
		}

	def onOk(self, event):
		result = self.validate()
		if not result:
			return
		self.result = result
		self.EndModal(wx.ID_OK)
