# -*- coding: utf-8 -*-

import addonHandler
import gui
from gui import guiHelper, nvdaControls
from gui.settingsDialogs import SettingsPanel
import shutil
import wx

from .config_io import loadConfigFromPathStrict, saveConfig
from .constants import (
	ALL_FILES_WILDCARD,
	CONFIRM_CAPTION,
	ERROR_CAPTION,
	TEXT_SNIPPET_ACTION_TO_LABEL,
	TYPE_TO_LABEL,
	VERBOSITY_ADVANCED,
	VERBOSITY_BEGINNER,
	VERBOSITY_VALUES,
)
from .gestures import formatGestureForDisplay
from .item_dialog import InstantAccessItemDialog

addonHandler.initTranslation()


def _getActionSummary(action):
	itemType = action.get("type", "")
	if itemType == "TextSnippets":
		text_preview = (
			(action.get("path", "") or "").replace("\r\n", "\n").replace("\r", "\n").split("\n", 1)[0]
		)
		if len(text_preview) > 70:
			text_preview = text_preview[:67] + "..."
		actionLabel = TEXT_SNIPPET_ACTION_TO_LABEL.get(
			action.get("textAction", "type"), TEXT_SNIPPET_ACTION_TO_LABEL["type"]
		)
		return _("{action}: {preview}").format(action=actionLabel, preview=text_preview)
	if itemType == "Keystrokes":
		first_keystroke = (
			(action.get("path", "") or "").replace("\r\n", "\n").replace("\r", "\n").split("\n", 1)[0].strip()
		)
		if len(first_keystroke) > 70:
			first_keystroke = first_keystroke[:67] + "..."
		return first_keystroke
	if itemType == "NvdaCommands":
		return action.get("commandLabel", "") or action.get("path", "")
	details = action.get("path", "")
	if itemType == "Programs" and action.get("arguments", "").strip():
		details = f"{details} {action.get('arguments', '').strip()}"
	return details


def _getItemTypeLabel(item):
	actions = item.get("actions", [])
	if not actions:
		return ""
	if len(actions) == 1:
		itemType = actions[0].get("type", "")
		return TYPE_TO_LABEL.get(itemType, itemType).replace("&", "")
	# Translators: Type label for shortcut items containing multiple actions.
	return _("Multiple actions")


def _getItemDetails(item):
	actions = item.get("actions", [])
	if not actions:
		return ""
	first = _getActionSummary(actions[0])
	if len(actions) == 1:
		return first
	# Translators: Summary for items with multiple actions. {first} is the first action summary and {count} the total action count.
	return _("{first} (+{count} more)").format(first=first, count=len(actions) - 1)


class InstantAccessSettingsPanel(SettingsPanel):
	# Translators: Title of the instant Access settings panel.
	title = _("instant Access")
	configManager = None
	onConfigChanged = None
	onRunItem = None
	onVerbosityChanged = None

	def makeSettings(self, settingsSizer):
		sHelper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		self.listCtrl = nvdaControls.AutoWidthColumnListCtrl(
			self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN
		)
		# Translators: Column label for item name in the list.
		self.listCtrl.InsertColumn(0, _("Name"))
		# Translators: Column label for item type in the list.
		self.listCtrl.InsertColumn(1, _("Type"))
		# Translators: Column label for shortcut in the list.
		self.listCtrl.InsertColumn(2, _("Shortcut"))
		# Translators: Column label for details in the list.
		self.listCtrl.InsertColumn(3, _("Details"))
		sHelper.addItem(self.listCtrl, flag=wx.EXPAND, proportion=1)

		buttonHelper = guiHelper.ButtonHelper(wx.HORIZONTAL)
		# Translators: Label for the Add button in the settings panel.
		self.addButton = buttonHelper.addButton(self, label=_("&Add"))
		# Translators: Label for the Edit button in the settings panel.
		self.editButton = buttonHelper.addButton(self, label=_("&Edit"))
		# Translators: Label for the Delete button in the settings panel.
		self.deleteButton = buttonHelper.addButton(self, label=_("&Delete"))
		# Translators: Label for the Duplicate button in the settings panel.
		self.duplicateButton = buttonHelper.addButton(self, label=_("D&uplicate"))
		# Translators: Label for the Test button in the settings panel.
		self.testButton = buttonHelper.addButton(self, label=_("&Test"))
		# Translators: Label for the Export settings button.
		self.exportButton = buttonHelper.addButton(self, label=_("E&xport settings"))
		# Translators: Label for the Import settings button.
		self.importButton = buttonHelper.addButton(self, label=_("I&mport settings"))
		sHelper.addItem(buttonHelper.sizer, flag=wx.EXPAND)

		# Translators: Label for verbosity level selection.
		self.verbosityChoice = sHelper.addLabeledControl(
			_("Verbosity level"), wx.Choice, choices=[VERBOSITY_BEGINNER, VERBOSITY_ADVANCED]
		)
		currentVerbosity = (
			self.configManager.getVerbosityLevel() if self.configManager else VERBOSITY_VALUES[0]
		)
		self.verbosityChoice.SetSelection(VERBOSITY_VALUES.index(currentVerbosity))

		self.addButton.Bind(wx.EVT_BUTTON, self.onAdd)
		self.editButton.Bind(wx.EVT_BUTTON, self.onEdit)
		self.deleteButton.Bind(wx.EVT_BUTTON, self.onDelete)
		self.duplicateButton.Bind(wx.EVT_BUTTON, self.onDuplicate)
		self.testButton.Bind(wx.EVT_BUTTON, self.onTest)
		self.exportButton.Bind(wx.EVT_BUTTON, self.onExportSettings)
		self.importButton.Bind(wx.EVT_BUTTON, self.onImportSettings)
		self.listCtrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onSelectionChange)
		self.listCtrl.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.onSelectionChange)
		self.listCtrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.onEdit)
		self.listCtrl.Bind(wx.EVT_KEY_DOWN, self.onListKeyDown)

		self.refreshList()
		self.updateButtons()

	def onListKeyDown(self, event):
		keyCode = event.GetKeyCode()
		if keyCode == wx.WXK_DELETE:
			self.onDelete(event)
		else:
			event.Skip()

	def onSave(self):
		verbosityValue = VERBOSITY_VALUES[self.verbosityChoice.GetSelection()]
		self.configManager.setVerbosityLevel(verbosityValue)
		if self.onVerbosityChanged:
			self.onVerbosityChanged(verbosityValue)

	def onSelectionChange(self, event):
		self.updateButtons()

	def updateButtons(self):
		hasSelection = self.listCtrl.GetFirstSelected() != -1
		self.editButton.Enable(hasSelection)
		self.deleteButton.Enable(hasSelection)
		self.duplicateButton.Enable(hasSelection)
		self.testButton.Enable(hasSelection)

	def refreshList(self, selectName=None):
		self.listCtrl.DeleteAllItems()
		self.items = self.configManager.getItems() if self.configManager else []
		selectedIndex = -1
		for index, item in enumerate(self.items):
			typeLabel = _getItemTypeLabel(item)
			gestureText = ", ".join([formatGestureForDisplay(g) for g in item.get("gestures", [])])
			self.listCtrl.InsertItem(index, item["name"])
			self.listCtrl.SetItem(index, 1, typeLabel)
			self.listCtrl.SetItem(index, 2, gestureText)
			self.listCtrl.SetItem(index, 3, _getItemDetails(item))
			if selectName and item["name"] == selectName:
				selectedIndex = index
		if selectedIndex >= 0:
			self.listCtrl.Select(selectedIndex)
			self.listCtrl.Focus(selectedIndex)
			self.listCtrl.SetFocus()
		self.updateButtons()

	def getSelectedItem(self):
		index = self.listCtrl.GetFirstSelected()
		if index == -1:
			return None
		try:
			return self.items[index]
		except Exception:
			return None

	def _saveItemResult(self, result, oldName=None):
		"""Persist a dialog result and refresh the UI.

		When *oldName* is given the existing item is updated; otherwise a new item is added.
		"""
		if oldName:
			self.configManager.updateItem(
				oldName,
				result["name"],
				result["gesture"],
				result.get("actions", []),
				result.get("interval", 0.0),
				result.get("appName", ""),
				result.get("stopOnError", True),
			)
		else:
			self.configManager.addItem(
				result["name"],
				result["gesture"],
				result.get("actions", []),
				result.get("interval", 0.0),
				result.get("appName", ""),
				result.get("stopOnError", True),
			)
		self.refreshList(selectName=result["name"])
		if self.onConfigChanged:
			self.onConfigChanged()

	def onAdd(self, event):
		# Translators: Title of the add item dialog.
		dialog = InstantAccessItemDialog(self, self.configManager, _("Add item"))
		if dialog.ShowModal() == wx.ID_OK:
			self._saveItemResult(dialog.result)
		dialog.Destroy()
		self.listCtrl.SetFocus()

	def onEdit(self, event):
		item = self.getSelectedItem()
		if not item:
			return
		# Translators: Title of the edit item dialog.
		dialog = InstantAccessItemDialog(self, self.configManager, _("Edit item"), existingItem=item)
		if dialog.ShowModal() == wx.ID_OK:
			self._saveItemResult(dialog.result, oldName=item["name"])
		dialog.Destroy()
		self.listCtrl.SetFocus()

	def onDuplicate(self, event):
		item = self.getSelectedItem()
		if not item:
			return
		uniqueName = self.configManager.getUniqueItemName(item.get("name", ""))
		clonedItem = dict(item)
		clonedItem["name"] = uniqueName
		clonedItem["gestures"] = []
		# Translators: Title of the duplicate item dialog.
		dialog = InstantAccessItemDialog(self, self.configManager, _("Duplicate item"), existingItem=clonedItem)
		if dialog.ShowModal() == wx.ID_OK:
			self._saveItemResult(dialog.result)
		dialog.Destroy()
		self.listCtrl.SetFocus()

	def onDelete(self, event):
		item = self.getSelectedItem()
		if not item:
			return
		deletedIndex = self.listCtrl.GetFirstSelected()
		if (
			gui.messageBox(
				_("Are you sure you would like to delete the selected item?"),
				CONFIRM_CAPTION,
				wx.YES_NO | wx.ICON_QUESTION,
			)
			== wx.YES
		):
			self.configManager.deleteItem(item["name"])
			self.refreshList()
			if self.items:
				if deletedIndex < 0:
					deletedIndex = 0
				nextIndex = min(deletedIndex, len(self.items) - 1)
				self.listCtrl.Select(nextIndex)
				self.listCtrl.Focus(nextIndex)
			if self.onConfigChanged:
				self.onConfigChanged()
		self.listCtrl.SetFocus()

	def onTest(self, event):
		item = self.getSelectedItem()
		if not item:
			return
		if self.onRunItem:
			self.onRunItem(item)
		self.listCtrl.SetFocus()

	def onExportSettings(self, event):
		if not self.configManager:
			return
		dialog = wx.FileDialog(
			self,
			_("Export settings"),
			wildcard=ALL_FILES_WILDCARD,
			style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
		)
		dialog.SetFilename("config.json")
		if dialog.ShowModal() == wx.ID_OK:
			destinationPath = dialog.GetPath()
			try:
				shutil.copy2(self.configManager.getConfigPath(), destinationPath)
				# Translators: Message shown when settings are successfully exported.
				gui.messageBox(_("Settings exported successfully."), self.title, wx.OK | wx.ICON_INFORMATION)
			except Exception:
				gui.messageBox(_("Could not export settings."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
		dialog.Destroy()
		self.listCtrl.SetFocus()

	def onImportSettings(self, event):
		if not self.configManager:
			return
		if (
			gui.messageBox(
				# Translators: Warning message before importing settings which will overwrite current configuration.
				_("Importing settings will replace your current items. Are you sure you want to continue?"),
				CONFIRM_CAPTION,
				wx.YES_NO | wx.ICON_QUESTION,
			)
			!= wx.YES
		):
			return
		dialog = wx.FileDialog(
			self,
			_("Import settings"),
			wildcard=ALL_FILES_WILDCARD,
			style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
		)
		if dialog.ShowModal() == wx.ID_OK:
			sourcePath = dialog.GetPath()
			try:
				testConfig = loadConfigFromPathStrict(sourcePath)
				saveConfig(self.configManager.getConfigPath(), testConfig)
				self.refreshList()
				currentVerbosity = self.configManager.getVerbosityLevel()
				self.verbosityChoice.SetSelection(VERBOSITY_VALUES.index(currentVerbosity))
				if self.onConfigChanged:
					self.onConfigChanged()
				if self.onVerbosityChanged:
					self.onVerbosityChanged(currentVerbosity)
				# Translators: Message shown when settings are successfully imported.
				gui.messageBox(_("Settings imported successfully."), self.title, wx.OK | wx.ICON_INFORMATION)
			except Exception:
				gui.messageBox(_("Could not import settings."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
		dialog.Destroy()
		self.listCtrl.SetFocus()
