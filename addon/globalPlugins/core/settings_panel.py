# -*- coding: utf-8 -*-

import addonHandler
import gui
from gui import guiHelper, nvdaControls
from gui.settingsDialogs import SettingsPanel
import shutil
import wx

from .config_io import DiskWriteDisabledError, loadConfigFromPathStrict
from .constants import (
	ANNOUNCE_VALUES,
	ALL_FILES_WILDCARD,
	BROWSE_FORMAT_LABELS,
	BROWSE_FORMAT_VALUES,
	BROWSE_ORDER_LABELS,
	BROWSE_ORDER_VALUES,
	CONFIRM_CAPTION,
	ERROR_CAPTION,
	TYPE_TO_LABEL,
	VERBOSITY_ADVANCED,
	VERBOSITY_BEGINNER,
	VERBOSITY_VALUES,
)
from .gestures import gestureDisplayText
from .item_dialog import (
	SWITCH_DELAY_SECONDS,
	InstantAccessItemDialog,
	actionDetails,
	actionsNeedSwitchDelay,
	confirmSwitchDelay,
)

addonHandler.initTranslation()


def _showSaveError(error, message):
	if isinstance(error, DiskWriteDisabledError):
		# Translators: Error shown when NVDA runs from the launcher or in secure mode, where settings cannot be saved.
		message = _("NVDA is running from the launcher or in secure mode, so settings cannot be saved.")
	gui.messageBox(message, ERROR_CAPTION, wx.OK | wx.ICON_ERROR)


def _mergeResult(added, skipped):
	# Translators: First part of the result of merging imported items; {count} is a number.
	addedText = ngettext("{count} item added.", "{count} items added.", added).format(count=added)
	# Translators: Second part of the result of merging imported items; {count} is a number.
	skippedText = ngettext("{count} item skipped.", "{count} items skipped.", skipped).format(count=skipped)
	return f"{addedText} {skippedText}"


def _getItemListName(item):
	if item.get("enabled", True):
		return item["name"]
	# Translators: An item name in the settings list when the item is turned off.
	return _("{name} (disabled)").format(name=item["name"])


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
	first = actionDetails(actions[0], maxLength=70)
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
	getPreviousAppName = None
	onVerbosityChanged = None
	executionQueue = None

	def makeSettings(self, settingsSizer):
		sHelper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		# Translators: Label of the field that narrows the item list by name.
		self.filterCtrl = sHelper.addLabeledControl(_("&Filter"), wx.TextCtrl)
		self.listCtrl = nvdaControls.AutoWidthColumnListCtrl(
			self,
			style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN,
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
			# Translators: Label of the choice between spoken messages and short tones.
			_("Verbosity level"),
			wx.Choice,
			choices=[VERBOSITY_BEGINNER, VERBOSITY_ADVANCED],
		)
		self.announceNameCheckBox = sHelper.addItem(
			# Translators: Checkbox for speaking an item's name when it runs; items can override it.
			wx.CheckBox(self, label=_("Announce the item &name when it runs")),
		)
		self.browseCheckBox = sHelper.addItem(
			# Translators: Checkbox enabling arrow/Tab browsing of items inside the instant Access layer.
			wx.CheckBox(self, label=_("Enable &browsing items in the instant Access layer")),
		)
		self.browseFormatChoice = sHelper.addLabeledControl(
			# Translators: Label for choosing how browsed items are announced.
			_("Browse &announcement"),
			wx.Choice,
			choices=BROWSE_FORMAT_LABELS,
		)
		self.browseOrderChoice = sHelper.addLabeledControl(
			# Translators: Label for choosing the order of browsed items.
			_("Browse &order"),
			wx.Choice,
			choices=BROWSE_ORDER_LABELS,
		)
		self.loadSettingsControls()
		self.browseCheckBox.Bind(wx.EVT_CHECKBOX, lambda event: self.updateBrowseControls())

		self.addButton.Bind(wx.EVT_BUTTON, self.onAdd)
		self.editButton.Bind(wx.EVT_BUTTON, self.onEdit)
		self.deleteButton.Bind(wx.EVT_BUTTON, self.onDelete)
		self.duplicateButton.Bind(wx.EVT_BUTTON, self.onDuplicate)
		self.testButton.Bind(wx.EVT_BUTTON, self.onTest)
		self.exportButton.Bind(wx.EVT_BUTTON, self.onExportSettings)
		self.importButton.Bind(wx.EVT_BUTTON, self.onImportSettings)
		self.filterCtrl.Bind(wx.EVT_TEXT, lambda event: self.refreshList())
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
		elif event.ControlDown() and keyCode == wx.WXK_UP:
			self._moveSelectedItem(-1)
		elif event.ControlDown() and keyCode == wx.WXK_DOWN:
			self._moveSelectedItem(1)
		else:
			event.Skip()

	def _moveSelectedItem(self, step):
		item = self.getSelectedItem()
		# The filtered list does not show the real neighbours.
		if not item or self.filterCtrl.GetValue().strip():
			return
		try:
			moved = self.configManager.moveItem(item["name"], step)
		except (OSError, ValueError) as error:
			# Translators: Error shown when the new order of the items could not be saved.
			_showSaveError(error, _("Could not save the order of the items."))
			return
		if moved:
			self.refreshList(selectName=item["name"])
			if self.onConfigChanged:
				self.onConfigChanged()

	def loadSettingsControls(self):
		settings = self.configManager.getSettings() if self.configManager else {}
		self.verbosityChoice.SetSelection(VERBOSITY_VALUES.index(settings.get("verbosity", VERBOSITY_VALUES[0])))
		self.announceNameCheckBox.SetValue(bool(settings.get("announceName", True)))
		self.browseCheckBox.SetValue(bool(settings.get("browseEnabled", False)))
		self.browseFormatChoice.SetSelection(
			BROWSE_FORMAT_VALUES.index(settings.get("browseFormat", BROWSE_FORMAT_VALUES[0])),
		)
		self.browseOrderChoice.SetSelection(
			BROWSE_ORDER_VALUES.index(settings.get("browseOrder", BROWSE_ORDER_VALUES[0])),
		)
		self.updateBrowseControls()

	def updateBrowseControls(self):
		enabled = self.browseCheckBox.GetValue()
		self.browseFormatChoice.Enable(enabled)
		self.browseOrderChoice.Enable(enabled)

	def onSave(self):
		verbosityValue = VERBOSITY_VALUES[self.verbosityChoice.GetSelection()]
		try:
			self.configManager.updateSettings(
				verbosity=verbosityValue,
				announceName=self.announceNameCheckBox.GetValue(),
				browseEnabled=self.browseCheckBox.GetValue(),
				browseFormat=BROWSE_FORMAT_VALUES[self.browseFormatChoice.GetSelection()],
				browseOrder=BROWSE_ORDER_VALUES[self.browseOrderChoice.GetSelection()],
			)
		except (OSError, ValueError) as error:
			# Translators: Error shown when the add-on settings could not be saved.
			_showSaveError(error, _("Could not save settings."))
			return
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
		query = self.filterCtrl.GetValue().strip().casefold()
		if selectName and query not in selectName.casefold():
			# The item just saved would otherwise vanish with no message.
			self.filterCtrl.ChangeValue("")
			query = ""
		allItems = self.configManager.getItems() if self.configManager else []
		self.items = [item for item in allItems if query in item["name"].casefold()]
		selectedIndex = -1
		for index, item in enumerate(self.items):
			typeLabel = _getItemTypeLabel(item)
			gestureText = ", ".join(gestureDisplayText(g) for g in item.get("gestures", []))
			self.listCtrl.InsertItem(index, _getItemListName(item))
			self.listCtrl.SetItem(index, 1, typeLabel)
			self.listCtrl.SetItem(index, 2, gestureText)
			self.listCtrl.SetItem(index, 3, _getItemDetails(item))
			if selectName and item["name"] == selectName:
				selectedIndex = index
		if selectedIndex >= 0:
			self.listCtrl.Select(selectedIndex)
			self.listCtrl.Focus(selectedIndex)
			self.listCtrl.SetFocus()
		elif query and self.items:
			# Focus stays in the filter field; Tab then lands on the first match.
			self.listCtrl.Select(0)
			self.listCtrl.Focus(0)
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
		"""Persist a dialog result and refresh the UI; oldName replaces that item in place."""
		try:
			self.configManager.saveItem(
				oldName,
				result["name"],
				result["gesture"],
				result.get("actions", []),
				interval=result.get("interval", 0.0),
				appName=result.get("appName", ""),
				stopOnError=result.get("stopOnError", True),
				enabled=result.get("enabled", True),
				announceName=result.get("announceName", ANNOUNCE_VALUES[0]),
			)
		except (OSError, ValueError) as error:
			_showSaveError(
				error,
				# Translators: Error shown when an item could not be saved.
				_("Could not save settings. Restore or import a valid configuration and try again."),
			)
			return False
		self.refreshList(selectName=result["name"])
		if self.onConfigChanged:
			self.onConfigChanged()
		return True

	def _runItemDialog(self, title, existingItem=None, oldName=None):
		dialog = InstantAccessItemDialog(self, self.configManager, title, existingItem=existingItem)
		while dialog.ShowModal() == wx.ID_OK:
			if self._saveItemResult(dialog.result, oldName=oldName):
				break
		dialog.Destroy()
		self.listCtrl.SetFocus()

	def onAdd(self, event):
		# Translators: Title of the add item dialog.
		self._runItemDialog(_("Add item"))

	def onEdit(self, event):
		item = self.getSelectedItem()
		if item:
			# Translators: Title of the edit item dialog.
			self._runItemDialog(_("Edit item"), existingItem=item, oldName=item["name"])

	def onDuplicate(self, event):
		item = self.getSelectedItem()
		if not item:
			return
		clonedItem = dict(item)
		clonedItem["name"] = self.configManager.getUniqueItemName(item.get("name", ""))
		clonedItem["gestures"] = []
		# Translators: Title of the duplicate item dialog.
		self._runItemDialog(_("Duplicate item"), existingItem=clonedItem)

	def onDelete(self, event):
		item = self.getSelectedItem()
		if not item:
			return
		deletedIndex = self.listCtrl.GetFirstSelected()
		if (
			gui.messageBox(
				# Translators: Question before deleting an item.
				_("Are you sure you would like to delete the selected item?"),
				CONFIRM_CAPTION,
				wx.YES_NO | wx.ICON_QUESTION,
			)
			== wx.YES
		):
			try:
				self.configManager.deleteItem(item["name"])
			except (OSError, ValueError) as error:
				# Translators: Error shown when deleting an item could not be saved.
				_showSaveError(error, _("Could not save settings."))
				return
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
		preDelay = 0
		if actionsNeedSwitchDelay(item.get("actions", [])):
			# Without the delay the item types into this settings window.
			if not confirmSwitchDelay():
				self.listCtrl.SetFocus()
				return
			preDelay = SWITCH_DELAY_SECONDS
		if self.onRunItem:
			self.onRunItem(item, preDelay=preDelay)
		self.listCtrl.SetFocus()

	def onExportSettings(self, event):
		if not self.configManager:
			return
		dialog = wx.FileDialog(
			self,
			# Translators: Title of the file dialog for exporting settings.
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
				# Translators: Error shown when the settings file could not be exported.
				gui.messageBox(_("Could not export settings."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
		dialog.Destroy()
		self.listCtrl.SetFocus()

	def onImportSettings(self, event):
		if not self.configManager:
			return
		dialog = wx.FileDialog(
			self,
			# Translators: Title of the file dialog for importing settings.
			_("Import settings"),
			wildcard=ALL_FILES_WILDCARD,
			style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
		)
		sourcePath = dialog.GetPath() if dialog.ShowModal() == wx.ID_OK else ""
		dialog.Destroy()
		if sourcePath:
			try:
				importedConfig = loadConfigFromPathStrict(sourcePath)
				answer = self._askImportMode()
				if answer == wx.ID_YES:
					self.configManager.replaceConfig(importedConfig)
					self._refreshAfterReplace()
					# Translators: Message shown when settings are successfully imported.
					gui.messageBox(_("Settings imported successfully."), self.title, wx.OK | wx.ICON_INFORMATION)
				elif answer == wx.ID_NO:
					added, skipped = self.configManager.mergeItems(importedConfig)
					self.refreshList()
					if self.onConfigChanged:
						self.onConfigChanged()
					gui.messageBox(_mergeResult(added, skipped), self.title, wx.OK | wx.ICON_INFORMATION)
			except Exception as error:
				# Translators: Error shown when a settings file could not be imported.
				_showSaveError(error, _("Could not import settings."))
		self.listCtrl.SetFocus()

	def _askImportMode(self):
		dialog = wx.MessageDialog(
			self,
			# Translators: Question after a settings file was chosen for import.
			_("Replace all your items and settings with this file, or add its new items to your current ones?"),
			CONFIRM_CAPTION,
			wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION,
		)
		# Translators: Buttons of the import question: replace everything, add new items, or stop.
		dialog.SetYesNoCancelLabels(_("&Replace"), _("&Merge"), _("&Cancel"))
		answer = dialog.ShowModal()
		dialog.Destroy()
		return answer

	def _refreshAfterReplace(self):
		self.refreshList()
		currentVerbosity = self.configManager.getVerbosityLevel()
		self.loadSettingsControls()
		if self.onConfigChanged:
			self.onConfigChanged()
		if self.onVerbosityChanged:
			self.onVerbosityChanged(currentVerbosity)
