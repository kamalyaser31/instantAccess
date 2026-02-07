# -*- coding: utf-8 -*-
# instantAccess.py
# instant Access add-on for NVDA
# Copyright (C) 2026 Kamal Yaser
# Copyright (C) 2026 Kamal Yaser
# Copyright (C) 2015 wafiq taher
# it under the terms of the GNU General Public License as published by
# You should have received a copy of the GNU General Public License
# along with this add-on. If not, see <https://www.gnu.org/licenses/>.
# See the file COPYING for more details.

import addonHandler
addonHandler.initTranslation()

from concurrent.futures import ThreadPoolExecutor
import configparser
import globalVars
import gui
from gui import guiHelper, nvdaControls
from gui.settingsDialogs import SettingsPanel
import globalPluginHandler
import inputCore
import keyboardHandler
import os
import shutil
import scriptHandler
import subprocess
import tones
import ui
import webbrowser
import wx


CONFIG_SECTIONS = ["Websites", "Programs", "Folders", "Files", "Gestures", "Arguments", "Settings"]
TYPE_SECTIONS = ["Websites", "Programs", "Folders", "Files"]
# Translators: Item types for instant Access entries.
TYPE_LABELS = [_("Website"), _("Program"), _("Folder"), _("File")]
RESERVED_GESTURES = {"kb:escape", "kb:nvda+e"}
# Translators: Category name for the instant Access add-on.
CATEGORY_LABEL = _("instant Access")
# Translators: Description for the toggle instant mode command in Input Gestures.
TOGGLE_DESCRIPTION = _("Toggle instant Access mode.")
# Translators: Caption for error message dialogs.
ERROR_CAPTION = _("Error")
# Translators: Caption for confirmation dialogs.
CONFIRM_CAPTION = _("Confirm")
# Translators: Wildcard for selecting any file in the file picker.
ALL_FILES_WILDCARD = _("All files (*.*)|*.*")
# Translators: Label for beginner verbosity level.
VERBOSITY_BEGINNER = _("Beginner")
# Translators: Label for advanced verbosity level.
VERBOSITY_ADVANCED = _("Advanced")
VERBOSITY_VALUES = ("beginner", "advanced")

# Config helpers
def ensureConfigParser():
	config = configparser.ConfigParser(delimiters=("="))
	config.optionxform = str
	return config


def ensureConfigFile(configPath):
	configDir = os.path.dirname(configPath)
	os.makedirs(configDir, exist_ok=True)
	if not os.path.exists(configPath):
		config = ensureConfigParser()
		for section in CONFIG_SECTIONS:
			config.add_section(section)
		with open(configPath, "w", encoding="utf-8") as handle:
			config.write(handle)


def loadConfigSafe(configPath):
	ensureConfigFile(configPath)
	config = ensureConfigParser()
	try:
		with open(configPath, "r", encoding="utf-8") as handle:
			config.read_file(handle)
	except (OSError, configparser.Error):
		config = ensureConfigParser()
		for section in CONFIG_SECTIONS:
			config.add_section(section)
		saveConfig(configPath, config)
	return config


def saveConfig(configPath, config):
	configDir = os.path.dirname(configPath)
	os.makedirs(configDir, exist_ok=True)
	with open(configPath, "w", encoding="utf-8") as handle:
		config.write(handle)

def formatGestureForDisplay(gesture):
	if not gesture:
		return ""
	gesture = gesture.strip()
	if gesture.lower().startswith("kb:"):
		return gesture[3:]
	return gesture


def normalizeGesture(gesture):
	if not gesture:
		return ""
	gesture = gesture.strip()
	if gesture.lower().startswith("kb:"):
		gesture = gesture[3:]
	gesture = gesture.strip()
	if not gesture:
		return ""
	return "kb:" + gesture.lower()


def validateGestureName(gestureName):
	if not gestureName:
		return False
	try:
		keyboardHandler.KeyboardInputGesture.fromName(gestureName)
		return True
	except Exception:
		return False


def getKeyNameFromEvent(event):
	keyCode = event.GetKeyCode()
	if keyCode in (wx.WXK_SHIFT, wx.WXK_CONTROL, wx.WXK_ALT, wx.WXK_WINDOWS_LEFT, wx.WXK_WINDOWS_RIGHT):
		return ""
	if wx.WXK_F1 <= keyCode <= wx.WXK_F24:
		return f"f{keyCode - wx.WXK_F1 + 1}"
	if wx.WXK_NUMPAD0 <= keyCode <= wx.WXK_NUMPAD9:
		return f"numpad{keyCode - wx.WXK_NUMPAD0}"
	keyMap = {
		wx.WXK_RETURN: "enter",
		wx.WXK_ESCAPE: "escape",
		wx.WXK_SPACE: "space",
		wx.WXK_TAB: "tab",
		wx.WXK_BACK: "backspace",
		wx.WXK_DELETE: "delete",
		wx.WXK_INSERT: "insert",
		wx.WXK_HOME: "home",
		wx.WXK_END: "end",
		wx.WXK_PAGEUP: "pageup",
		wx.WXK_PAGEDOWN: "pagedown",
		wx.WXK_LEFT: "leftArrow",
		wx.WXK_RIGHT: "rightArrow",
		wx.WXK_UP: "upArrow",
		wx.WXK_DOWN: "downArrow",
		wx.WXK_ADD: "numpadPlus",
		wx.WXK_SUBTRACT: "numpadMinus",
		wx.WXK_MULTIPLY: "numpadMultiply",
		wx.WXK_DIVIDE: "numpadDivide",
		wx.WXK_NUMPAD_DECIMAL: "numpadDecimal",
		wx.WXK_NUMPAD_ENTER: "numpadEnter",
	}
	if keyCode in keyMap:
		return keyMap[keyCode]
	unicodeKey = event.GetUnicodeKey()
	if unicodeKey != wx.WXK_NONE and unicodeKey >= 32:
		char = chr(unicodeKey)
		return char.lower()
	if 32 <= keyCode <= 126:
		return chr(keyCode).lower()
	return ""


def buildGestureNameFromEvent(event):
	keyName = getKeyNameFromEvent(event)
	if not keyName:
		return ""
	modifiers = []
	if event.ControlDown():
		modifiers.append("control")
	if event.AltDown():
		modifiers.append("alt")
	if event.ShiftDown():
		modifiers.append("shift")
	if event.MetaDown():
		modifiers.append("windows")
	return "+".join(modifiers + [keyName])


def expandGestureLayouts(gesture):
	gesture = (gesture or "").strip()
	if not gesture:
		return []
	if gesture.lower().startswith("kb:"):
		return [gesture, "kb(laptop):" + gesture[3:]]
	return [gesture]


def normalizeGestureIdentifier(gestureId):
	if not gestureId:
		return ""
	gestureId = gestureId.strip().lower()
	if gestureId.startswith("kb("):
		closeIndex = gestureId.find("):")
		if closeIndex != -1:
			return "kb:" + gestureId[closeIndex + 2 :]
	return gestureId


def expandPath(rawPath):
	if not rawPath:
		return rawPath
	return os.path.expandvars(os.path.expanduser(rawPath))


def queueMessage(message):
	if message:
		wx.CallAfter(ui.message, message)


def executeInstantItem(itemType, path, arguments=""):
	if itemType == "Websites":
		url = (path or "").strip()
		if not url:
			# Translators: Error message when a URL is empty.
			queueMessage(_("Error: URL is empty"))
			return
		if not url.lower().startswith(("http://", "https://")):
			url = "https://" + url
		try:
			webbrowser.open(url)
		except Exception:
			# Translators: Error message when a website cannot be opened.
			queueMessage(_("Error: Could not open the website"))
		return
	resolvedPath = expandPath(path or "")
	if not resolvedPath or not os.path.exists(resolvedPath):
		# Translators: Error message when a file or folder is missing.
		queueMessage(_("Error: File not found"))
		return
	if itemType == "Folders":
		try:
			os.startfile(resolvedPath)
		except Exception:
			# Translators: Error message when a file or folder cannot be opened.
			queueMessage(_("Error: Could not open the item"))
		return
	if itemType == "Files":
		try:
			if not wx.LaunchDefaultApplication(resolvedPath):
				# Translators: Error message when a file cannot be opened with associated application.
				queueMessage(_("Error: Could not open the file"))
		except Exception:
			# Translators: Error message when a file cannot be opened with associated application.
			queueMessage(_("Error: Could not open the file"))
		return
	if itemType == "Programs":
		try:
			argumentsText = (arguments or "").strip()
			workingDir = os.path.dirname(resolvedPath) or None
			if argumentsText:
				commandLine = subprocess.list2cmdline([resolvedPath]) + " " + argumentsText
				subprocess.Popen(commandLine, cwd=workingDir)
			else:
				subprocess.Popen([resolvedPath], cwd=workingDir)
		except Exception:
			# Translators: Error message when a program cannot be started.
			queueMessage(_("Error: Could not start the program"))
		return


def wrapFinally(func, final):
	def wrapped(*args, **kwargs):
		try:
			return func(*args, **kwargs)
		finally:
			final()
	return wrapped


class ConfigManager:
	def __init__(self, configPath):
		self.configPath = configPath
		ensureConfigFile(self.configPath)

	def loadOrCreateConfig(self):
		config = loadConfigSafe(self.configPath)
		for section in CONFIG_SECTIONS:
			if not config.has_section(section):
				config.add_section(section)
		return config

	def saveConfig(self, config):
		saveConfig(self.configPath, config)

	def getConfigPath(self):
		return self.configPath

	def getItems(self):
		config = self.loadOrCreateConfig()
		gestureMap = {}
		argumentMap = {}
		if config.has_section("Gestures"):
			for gesture, name in config.items("Gestures"):
				gestureMap.setdefault(name, []).append(gesture)
		if config.has_section("Arguments"):
			for name, argumentText in config.items("Arguments"):
				argumentMap[name] = argumentText
		items = []
		for section in TYPE_SECTIONS:
			if not config.has_section(section):
				continue
			for name, path in config.items(section):
				items.append({
					"name": name,
					"type": section,
					"path": path,
					"arguments": argumentMap.get(name, ""),
					"gestures": gestureMap.get(name, []),
				})
		return items

	def getAllNames(self):
		config = self.loadOrCreateConfig()
		allNames = set()
		for section in TYPE_SECTIONS:
			if not config.has_section(section):
				continue
			for name, _value in config.items(section):
				allNames.add(name)
		return allNames

	def getGestureToNameMap(self):
		config = self.loadOrCreateConfig()
		gestureMap = {}
		if config.has_section("Gestures"):
			for gesture, name in config.items("Gestures"):
				gestureMap[gesture.lower()] = name
		return gestureMap

	def removeGesturesForName(self, config, name):
		if not config.has_section("Gestures"):
			return
		toRemove = []
		for gesture, mappedName in config.items("Gestures"):
			if mappedName == name:
				toRemove.append(gesture)
		for gesture in toRemove:
			config.remove_option("Gestures", gesture)

	def addItem(self, name, itemType, path, gesture, arguments=""):
		config = self.loadOrCreateConfig()
		if not config.has_section(itemType):
			config.add_section(itemType)
		config.set(itemType, name, path)
		self.removeGesturesForName(config, name)
		if config.has_section("Arguments"):
			config.remove_option("Arguments", name)
		if itemType == "Programs" and arguments.strip():
			config.set("Arguments", name, arguments.strip())
		if gesture:
			config.set("Gestures", gesture, name)
		self.saveConfig(config)

	def updateItem(self, oldName, name, itemType, path, gesture, arguments=""):
		config = self.loadOrCreateConfig()
		for section in TYPE_SECTIONS:
			if config.has_section(section) and config.has_option(section, oldName):
				config.remove_option(section, oldName)
		if not config.has_section(itemType):
			config.add_section(itemType)
		config.set(itemType, name, path)
		if config.has_section("Arguments"):
			config.remove_option("Arguments", oldName)
			config.remove_option("Arguments", name)
		if itemType == "Programs" and arguments.strip():
			config.set("Arguments", name, arguments.strip())
		self.removeGesturesForName(config, oldName)
		self.removeGesturesForName(config, name)
		if gesture:
			config.set("Gestures", gesture, name)
		self.saveConfig(config)

	def deleteItem(self, name):
		config = self.loadOrCreateConfig()
		for section in TYPE_SECTIONS:
			if config.has_section(section):
				config.remove_option(section, name)
		if config.has_section("Arguments"):
			config.remove_option("Arguments", name)
		self.removeGesturesForName(config, name)
		self.saveConfig(config)

	def getVerbosityLevel(self):
		config = self.loadOrCreateConfig()
		if not config.has_section("Settings"):
			config.add_section("Settings")
		value = config.get("Settings", "verbosity", fallback=VERBOSITY_VALUES[0]).strip().lower()
		if value not in VERBOSITY_VALUES:
			value = VERBOSITY_VALUES[0]
		return value

	def setVerbosityLevel(self, value):
		config = self.loadOrCreateConfig()
		if not config.has_section("Settings"):
			config.add_section("Settings")
		value = (value or "").strip().lower()
		if value not in VERBOSITY_VALUES:
			value = VERBOSITY_VALUES[0]
		config.set("Settings", "verbosity", value)
		self.saveConfig(config)


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


class instantAccessItemDialog(wx.Dialog):
	def __init__(self, parent, configManager, title, existingItem=None):
		wx.Dialog.__init__(self, parent, title=title, style=wx.DEFAULT_DIALOG_STYLE)
		self.configManager = configManager
		self.existingItem = existingItem
		self.gesture = ""

		panel = wx.Panel(self)
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		sizerHelper = guiHelper.BoxSizerHelper(panel, wx.VERTICAL)

		# Translators: Label for the name field in the add/edit dialog.
		self.nameCtrl = sizerHelper.addLabeledControl(_("Name"), wx.TextCtrl)
		# Translators: Label for the type field in the add/edit dialog.
		self.typeChoice = sizerHelper.addLabeledControl(_("Type"), wx.Choice, choices=TYPE_LABELS)
		self.typeChoice.SetSelection(0)

		pathSizer = wx.BoxSizer(wx.HORIZONTAL)
		# Translators: Label for the path or URL field in the add/edit dialog.
		pathLabel = wx.StaticText(panel, wx.ID_ANY, _("Path or URL"))
		self.pathCtrl = wx.TextCtrl(panel, wx.ID_ANY)
		# Translators: Label for the browse button in the add/edit dialog.
		self.browseButton = wx.Button(panel, wx.ID_ANY, _("Browse"))
		pathSizer.Add(pathLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		pathSizer.Add(self.pathCtrl, 1, wx.RIGHT, guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		pathSizer.Add(self.browseButton, 0)
		sizerHelper.addItem(pathSizer, flag=wx.EXPAND)

		# Translators: Label for optional command line arguments in the add/edit dialog.
		self.argumentsCtrl = sizerHelper.addLabeledControl(_("Arguments (optional)"), wx.TextCtrl)

		shortcutSizer = wx.BoxSizer(wx.HORIZONTAL)
		# Translators: Label for the shortcut section in the add/edit dialog.
		shortcutLabel = wx.StaticText(panel, wx.ID_ANY, _("Shortcut"))
		self.shortcutButton = wx.Button(panel, wx.ID_ANY, "")
		shortcutSizer.Add(shortcutLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, guiHelper.SPACE_BETWEEN_ASSOCIATED_CONTROL_HORIZONTAL)
		shortcutSizer.Add(self.shortcutButton, 0)
		sizerHelper.addItem(shortcutSizer)

		buttonSizer = guiHelper.ButtonHelper(wx.HORIZONTAL)
		# Translators: Label for the OK button in the add/edit dialog.
		self.okButton = buttonSizer.addButton(panel, wx.ID_OK, _("&OK"))
		# Translators: Label for the Cancel button in the add/edit dialog.
		self.cancelButton = buttonSizer.addButton(panel, wx.ID_CANCEL, _("&Cancel"))

		mainSizer.Add(sizerHelper.sizer, 0, wx.ALL | wx.EXPAND, 10)
		mainSizer.Add(buttonSizer.sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)
		panel.SetSizerAndFit(mainSizer)
		self.Fit()

		self.Bind(wx.EVT_CHOICE, self.onTypeChange, self.typeChoice)
		self.Bind(wx.EVT_BUTTON, self.onBrowse, self.browseButton)
		self.Bind(wx.EVT_BUTTON, self.onSetShortcut, self.shortcutButton)
		self.Bind(wx.EVT_BUTTON, self.onOk, self.okButton)
		self.Bind(wx.EVT_CHAR_HOOK, self.onCharHook)

		if existingItem:
			self.nameCtrl.SetValue(existingItem["name"])
			if existingItem["type"] in TYPE_SECTIONS:
				self.typeChoice.SetSelection(TYPE_SECTIONS.index(existingItem["type"]))
			self.pathCtrl.SetValue(existingItem["path"])
			self.argumentsCtrl.SetValue(existingItem.get("arguments", ""))
			gestures = existingItem.get("gestures", [])
			if gestures:
				self.gesture = normalizeGesture(gestures[0])
		self.updateShortcutLabel()

		self.updateBrowseState()
		self.CentreOnScreen()

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

	def updateBrowseState(self):
		itemType = TYPE_SECTIONS[self.typeChoice.GetSelection()]
		self.browseButton.Enable(itemType in ("Programs", "Folders", "Files"))
		self.argumentsCtrl.Enable(itemType == "Programs")
		if itemType != "Programs":
			self.argumentsCtrl.SetValue("")

	def onTypeChange(self, event):
		self.updateBrowseState()

	def onBrowse(self, event):
		itemType = TYPE_SECTIONS[self.typeChoice.GetSelection()]
		if itemType == "Programs":
			# Translators: Title of the file picker for selecting a program.
			dialog = wx.FileDialog(self, _("Select a program"), wildcard=ALL_FILES_WILDCARD, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
			if dialog.ShowModal() == wx.ID_OK:
				self.pathCtrl.SetValue(dialog.GetPath())
			dialog.Destroy()
			return
		if itemType == "Folders":
			# Translators: Title of the folder picker for selecting a folder.
			dialog = wx.DirDialog(self, _("Select a folder"), style=wx.DD_DIR_MUST_EXIST)
			if dialog.ShowModal() == wx.ID_OK:
				self.pathCtrl.SetValue(dialog.GetPath())
			dialog.Destroy()
			return
		if itemType == "Files":
			# Translators: Title of the file picker for selecting a file.
			dialog = wx.FileDialog(self, _("Select a file"), wildcard=ALL_FILES_WILDCARD, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
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
				# Translators: Error shown when a reserved shortcut is selected.
				gui.messageBox(_("This shortcut is reserved for instant Access."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
				dialog.Destroy()
				return
			if not validateGestureName(formatGestureForDisplay(gestureName)):
				# Translators: Error shown when an invalid shortcut is selected.
				gui.messageBox(_("Invalid shortcut key."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
				dialog.Destroy()
				return
			self.gesture = gestureName
			self.updateShortcutLabel()
		dialog.Destroy()

	def validate(self):
		name = self.nameCtrl.GetValue().strip()
		itemType = TYPE_SECTIONS[self.typeChoice.GetSelection()]
		path = self.pathCtrl.GetValue().strip()
		gesture = self.gesture
		arguments = self.argumentsCtrl.GetValue().strip() if itemType == "Programs" else ""

		if not name or not path or not gesture:
			# Translators: Error shown when required fields are missing.
			gui.messageBox(_("All fields are required."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None

		normalizedGesture = normalizeGesture(gesture)
		if normalizedGesture in RESERVED_GESTURES:
			# Translators: Error shown when a reserved shortcut is selected.
			gui.messageBox(_("This shortcut is reserved for instant Access."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None
		if not validateGestureName(formatGestureForDisplay(normalizedGesture)):
			# Translators: Error shown when an invalid shortcut is selected.
			gui.messageBox(_("Invalid shortcut key."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None

		allNames = self.configManager.getAllNames()
		if self.existingItem:
			allNames.discard(self.existingItem["name"])
		if name in allNames:
			# Translators: Error shown when a name is already in use.
			gui.messageBox(_("This name already exists."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None

		gestureMap = self.configManager.getGestureToNameMap()
		existingName = gestureMap.get(normalizedGesture.lower())
		if existingName and (not self.existingItem or existingName != self.existingItem["name"]):
			# Translators: Error shown when a shortcut is already assigned.
			gui.messageBox(_("This shortcut is already assigned."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return None

		return {
			"name": name,
			"type": itemType,
			"path": path,
			"arguments": arguments,
			"gesture": normalizedGesture,
		}

	def onOk(self, event):
		result = self.validate()
		if not result:
			return
		self.result = result
		self.EndModal(wx.ID_OK)


class instantAccessSettingsPanel(SettingsPanel):
	# Translators: Title of the instant Access settings panel.
	title = _("instant Access")
	configManager = None
	onConfigChanged = None
	onRunItem = None
	onVerbosityChanged = None

	def makeSettings(self, settingsSizer):
		sHelper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		self.listCtrl = nvdaControls.AutoWidthColumnListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN)
		# Translators: Column label for item name in the list.
		self.listCtrl.InsertColumn(0, _("Name"))
		# Translators: Column label for item type in the list.
		self.listCtrl.InsertColumn(1, _("Type"))
		# Translators: Column label for shortcut in the list.
		self.listCtrl.InsertColumn(2, _("Shortcut"))
		# Translators: Column label for path or URL in the list.
		self.listCtrl.InsertColumn(3, _("Path"))
		sHelper.addItem(self.listCtrl, flag=wx.EXPAND, proportion=1)

		buttonHelper = guiHelper.ButtonHelper(wx.HORIZONTAL)
		# Translators: Label for the Add button in the settings panel.
		self.addButton = buttonHelper.addButton(self, label=_("&Add"))
		# Translators: Label for the Edit button in the settings panel.
		self.editButton = buttonHelper.addButton(self, label=_("&Edit"))
		# Translators: Label for the Delete button in the settings panel.
		self.deleteButton = buttonHelper.addButton(self, label=_("&Delete"))
		# Translators: Label for the Test button in the settings panel.
		self.testButton = buttonHelper.addButton(self, label=_("&Test"))
		# Translators: Label for the Export settings button.
		self.exportButton = buttonHelper.addButton(self, label=_("E&xport settings"))
		# Translators: Label for the Import settings button.
		self.importButton = buttonHelper.addButton(self, label=_("I&mport settings"))
		sHelper.addItem(buttonHelper.sizer, flag=wx.EXPAND)

		# Translators: Label for verbosity level selection.
		self.verbosityChoice = sHelper.addLabeledControl(_("Verbosity level"), wx.Choice, choices=[VERBOSITY_BEGINNER, VERBOSITY_ADVANCED])
		currentVerbosity = self.configManager.getVerbosityLevel() if self.configManager else VERBOSITY_VALUES[0]
		self.verbosityChoice.SetSelection(VERBOSITY_VALUES.index(currentVerbosity))

		self.addButton.Bind(wx.EVT_BUTTON, self.onAdd)
		self.editButton.Bind(wx.EVT_BUTTON, self.onEdit)
		self.deleteButton.Bind(wx.EVT_BUTTON, self.onDelete)
		self.testButton.Bind(wx.EVT_BUTTON, self.onTest)
		self.exportButton.Bind(wx.EVT_BUTTON, self.onExportSettings)
		self.importButton.Bind(wx.EVT_BUTTON, self.onImportSettings)
		self.listCtrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onSelectionChange)
		self.listCtrl.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.onSelectionChange)

		self.refreshList()
		self.updateButtons()

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
		self.testButton.Enable(hasSelection)

	def refreshList(self, selectName=None):
		self.listCtrl.DeleteAllItems()
		self.items = self.configManager.getItems() if self.configManager else []
		selectedIndex = -1
		for index, item in enumerate(self.items):
			typeLabel = TYPE_LABELS[TYPE_SECTIONS.index(item["type"])].replace("&", "")
			gestureText = ", ".join([formatGestureForDisplay(g) for g in item.get("gestures", [])])
			self.listCtrl.InsertItem(index, item["name"])
			self.listCtrl.SetItem(index, 1, typeLabel)
			self.listCtrl.SetItem(index, 2, gestureText)
			self.listCtrl.SetItem(index, 3, item["path"])
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

	def onAdd(self, event):
		# Translators: Title of the add item dialog.
		dialog = instantAccessItemDialog(self, self.configManager, _("Add item"))
		if dialog.ShowModal() == wx.ID_OK:
			result = dialog.result
			self.configManager.addItem(result["name"], result["type"], result["path"], result["gesture"], result.get("arguments", ""))
			self.refreshList(selectName=result["name"])
			if self.onConfigChanged:
				self.onConfigChanged()
		dialog.Destroy()
		self.listCtrl.SetFocus()

	def onEdit(self, event):
		item = self.getSelectedItem()
		if not item:
			return
		# Translators: Title of the edit item dialog.
		dialog = instantAccessItemDialog(self, self.configManager, _("Edit item"), existingItem=item)
		if dialog.ShowModal() == wx.ID_OK:
			result = dialog.result
			self.configManager.updateItem(item["name"], result["name"], result["type"], result["path"], result["gesture"], result.get("arguments", ""))
			self.refreshList(selectName=result["name"])
			if self.onConfigChanged:
				self.onConfigChanged()
		dialog.Destroy()
		self.listCtrl.SetFocus()

	def onDelete(self, event):
		item = self.getSelectedItem()
		if not item:
			return
		deletedIndex = self.listCtrl.GetFirstSelected()
		# Translators: Confirmation prompt when deleting an item.
		if gui.messageBox(_("Are you sure you would like to delete the selected item?"), CONFIRM_CAPTION, wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
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
			# Translators: Title of the export settings dialog.
			_("Export settings"),
			wildcard=ALL_FILES_WILDCARD,
			style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
		)
		dialog.SetFilename("config.ini")
		if dialog.ShowModal() == wx.ID_OK:
			destinationPath = dialog.GetPath()
			try:
				shutil.copy2(self.configManager.getConfigPath(), destinationPath)
			except Exception:
				# Translators: Error shown when exporting settings fails.
				gui.messageBox(_("Could not export settings."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
		dialog.Destroy()
		self.listCtrl.SetFocus()

	def onImportSettings(self, event):
		if not self.configManager:
			return
		dialog = wx.FileDialog(
			self,
			# Translators: Title of the import settings dialog.
			_("Import settings"),
			wildcard=ALL_FILES_WILDCARD,
			style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
		)
		if dialog.ShowModal() == wx.ID_OK:
			sourcePath = dialog.GetPath()
			try:
				testConfig = ensureConfigParser()
				with open(sourcePath, "r", encoding="utf-8") as handle:
					testConfig.read_file(handle)
				for section in CONFIG_SECTIONS:
					if not testConfig.has_section(section):
						testConfig.add_section(section)
				saveConfig(self.configManager.getConfigPath(), testConfig)
				self.refreshList()
				currentVerbosity = self.configManager.getVerbosityLevel()
				self.verbosityChoice.SetSelection(VERBOSITY_VALUES.index(currentVerbosity))
				if self.onConfigChanged:
					self.onConfigChanged()
				if self.onVerbosityChanged:
					self.onVerbosityChanged(currentVerbosity)
			except Exception:
				# Translators: Error shown when importing settings fails.
				gui.messageBox(_("Could not import settings."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
		dialog.Destroy()
		self.listCtrl.SetFocus()


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self):
		super().__init__()
		if globalVars.appArgs.secure:
			return
		self.executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="instantAccess")
		self.verbosityLevel = VERBOSITY_VALUES[0]
		self.instantMode = False
		self.gestureToItem = {}
		self.loadedCommandCount = 0
		configPath = os.path.join(globalVars.appArgs.configPath, "instantAccess", "config.ini")
		self.configManager = ConfigManager(configPath)
		self.setVerbosityLevel(self.configManager.getVerbosityLevel())
		instantAccessSettingsPanel.configManager = self.configManager
		instantAccessSettingsPanel.onConfigChanged = self.onConfigChanged
		instantAccessSettingsPanel.onRunItem = self.queueRunItemExecution
		instantAccessSettingsPanel.onVerbosityChanged = self.setVerbosityLevel
		gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(instantAccessSettingsPanel)

	def terminate(self):
		if not hasattr(self, "executor"):
			return
		try:
			gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(instantAccessSettingsPanel)
		except Exception:
			pass
		instantAccessSettingsPanel.onRunItem = None
		instantAccessSettingsPanel.onVerbosityChanged = None
		self.deactivateInstantMode(speak=False)
		self.executor.shutdown(wait=False, cancel_futures=True)

	def onConfigChanged(self):
		if not hasattr(self, "instantMode"):
			return
		if self.instantMode:
			self.activateInstantMode(speak=False)

	def setVerbosityLevel(self, value):
		if value not in VERBOSITY_VALUES:
			value = VERBOSITY_VALUES[0]
		self.verbosityLevel = value

	def isAdvancedVerbosity(self):
		return self.verbosityLevel == VERBOSITY_VALUES[1]

	def queueTone(self, frequency, duration):
		wx.CallAfter(tones.beep, frequency, duration)

	def queueRunItemExecution(self, item):
		if not item:
			return
		self.executor.submit(self.runItemTask, dict(item))

	def runItemTask(self, item):
		commandName = (item.get("name", "") or "").strip()
		if commandName:
			wx.CallAfter(ui.message, commandName)
		executeInstantItem(
			itemType=item.get("type", ""),
			path=item.get("path", ""),
			arguments=item.get("arguments", ""),
		)

	def getScript(self, gesture):
		if not self.instantMode:
			return globalPluginHandler.GlobalPlugin.getScript(self, gesture)
		script = globalPluginHandler.GlobalPlugin.getScript(self, gesture)
		if not script:
			script = self.script_invalidKey
		return wrapFinally(script, self.finishInstantLayer)

	def getToggleGestures(self):
		try:
			mappings = inputCore.manager.getAllGestureMappings()
			categoryMap = mappings.get(CATEGORY_LABEL, {})
			scriptInfo = categoryMap.get(TOGGLE_DESCRIPTION)
			if scriptInfo and getattr(scriptInfo, "gestures", None):
				return list(scriptInfo.gestures)
		except Exception:
			pass
		return ["kb:NVDA+e"]

	def buildInstantGestures(self):
		items = self.configManager.getItems()
		self.gestureToItem = {}
		for item in items:
			for gesture in item.get("gestures", []):
				for expanded in expandGestureLayouts(gesture):
					self.gestureToItem[expanded.lower()] = item
		self.loadedCommandCount = len({item["name"] for item in self.gestureToItem.values()})
		instantGestures = {}
		for gesture in self.gestureToItem.keys():
			instantGestures[gesture] = "runInstantItem"
		for gesture in self.getToggleGestures():
			instantGestures[gesture] = "toggleInstantMode"
		instantGestures["kb:escape"] = "exitInstantMode"
		return instantGestures

	def activateInstantMode(self, speak=True):
		instantGestures = self.buildInstantGestures()
		if self.loadedCommandCount <= 0:
			self.instantMode = False
			self.clearGestureBindings()
			self.bindGestures({gesture: "toggleInstantMode" for gesture in self.getToggleGestures()})
			if speak:
				# Translators: Message announced when trying to enable instant Access mode with no configured commands.
				ui.message(_("No commands configured."))
			return
		self.instantMode = True
		self.clearGestureBindings()
		self.bindGestures(instantGestures)
		if speak:
			if self.isAdvancedVerbosity():
				# Translators: Short message announced in advanced verbosity when instant Access mode is enabled.
				ui.message(_("On"))
			else:
				count = self.loadedCommandCount
				# Translators: Message announced when instant Access mode is enabled. {count} is the number of commands.
				ui.message(_("instant Access On. {count} commands loaded").format(count=count))

	def deactivateInstantMode(self, speak=True):
		if not self.instantMode:
			return
		self.instantMode = False
		self.clearGestureBindings()
		self.bindGestures({gesture: "toggleInstantMode" for gesture in self.getToggleGestures()})
		if speak:
			if self.isAdvancedVerbosity():
				# Translators: Short message announced in advanced verbosity when instant Access mode is disabled.
				ui.message(_("Off"))
			else:
				# Translators: Message announced when instant Access mode is disabled.
				ui.message(_("instant Access Off"))

	def finishInstantLayer(self):
		if self.instantMode:
			self.deactivateInstantMode(speak=False)

	def script_invalidKey(self, gesture):
		if self.isAdvancedVerbosity():
			self.queueTone(250, 50)
			return
		# Translators: Message announced when a pressed key has no assigned command in instant Access mode.
		ui.message(_("This gesture has no command assigned."))
		tones.beep(250, 50)

	@scriptHandler.script(
		category=CATEGORY_LABEL,
		description=TOGGLE_DESCRIPTION,
		gesture="kb:NVDA+e",
	)
	def script_toggleInstantMode(self, gesture):
		if self.instantMode:
			self.deactivateInstantMode()
		else:
			self.activateInstantMode()

	def script_exitInstantMode(self, gesture):
		self.deactivateInstantMode()

	def script_runInstantItem(self, gesture):
		identifiers = []
		if hasattr(gesture, "identifiers") and gesture.identifiers:
			identifiers.extend(gesture.identifiers)
		elif hasattr(gesture, "identifier"):
			identifiers.append(gesture.identifier)
		item = None
		for gestureId in identifiers:
			normalized = normalizeGestureIdentifier(gestureId)
			item = self.gestureToItem.get(normalized)
			if item:
				break
		if not item:
			return
		self.queueRunItemExecution(item)
