# -*- coding: utf-8 -*-

from logHandler import log
import os

import addonHandler
import api
import globalPluginHandler
import globalVars
import gui
import scriptHandler
import tones
import ui
import wx

from .browse import (
	buildHelpText,
	formatItem,
	getUsableItems,
	resolveItem,
	shouldAnnounceName,
	sortItems,
)
from .config_manager import ConfigManager
from .constants import (
	ADDON_SCRIPT_GESTURES,
	BROWSE_GESTURES,
	CATEGORY_LABEL,
	DEFAULT_SETTINGS,
	REPORT_APP_NAME_DESCRIPTION,
	TOGGLE_DESCRIPTION,
	VERBOSITY_VALUES,
)
from .executor import ExecutionQueue, setClipboardText
from .gestures import gestureKey, getAddonGestures
from .settings_panel import InstantAccessSettingsPanel

addonHandler.initTranslation()



class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self):
		super().__init__()
		self._enabled = False
		self.verbosityLevel = VERBOSITY_VALUES[0]
		self.instantMode = False
		self.gestureToItems = {}
		self.loadedCommandCount = 0
		self.layerItems = []
		self.browseSettings = dict(DEFAULT_SETTINGS)
		self.browseGestureScripts = {}
		self._resetBrowseState()
		self._keepLayerOpen = False
		if globalVars.appArgs.secure:
			self.clearGestureBindings()
			return
		self.executionQueue = ExecutionQueue()
		self._enabled = True
		configPath = os.path.join(globalVars.appArgs.configPath, "instantAccess", "config.json")
		self.configManager = ConfigManager(configPath)
		self.setVerbosityLevel(self.configManager.getVerbosityLevel())
		InstantAccessSettingsPanel.configManager = self.configManager
		InstantAccessSettingsPanel.onConfigChanged = self.onConfigChanged
		InstantAccessSettingsPanel.onRunItem = self.queueRunItemExecution
		InstantAccessSettingsPanel.onVerbosityChanged = self.setVerbosityLevel
		InstantAccessSettingsPanel.executionQueue = self.executionQueue
		gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(InstantAccessSettingsPanel)

	def terminate(self):
		self._enabled = False
		if not hasattr(self, "executionQueue"):
			return
		self.executionQueue.shutdown()
		try:
			gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(InstantAccessSettingsPanel)
		except ValueError:
			# Item not in list, which is fine
			pass
		except Exception as e:
			log.error("instantAccess: Error removing settings panel during termination: %s", e, exc_info=True)

		InstantAccessSettingsPanel.configManager = None
		InstantAccessSettingsPanel.onConfigChanged = None
		InstantAccessSettingsPanel.onRunItem = None
		InstantAccessSettingsPanel.onVerbosityChanged = None
		InstantAccessSettingsPanel.executionQueue = None
		self.deactivateInstantMode(speak=False)
		self.clearGestureBindings()

	def onConfigChanged(self):
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

	def queueRunItemExecution(self, item, preDelay=0):
		if not item or not self._enabled:
			return
		announce = shouldAnnounceName(item, self.configManager.getSettings()["announceName"])
		return self.executionQueue.submit(item, preDelay=preDelay, announce=announce)

	def getScript(self, gesture):
		if not self._enabled:
			return None
		if not self.instantMode:
			return globalPluginHandler.GlobalPlugin.getScript(self, gesture)
		script = globalPluginHandler.GlobalPlugin.getScript(self, gesture)
		if not script:
			script = self.script_invalidKey

		def wrappedScript(*args, **kwargs):
			# Browse scripts set this so the layer stays open for the next key.
			self._keepLayerOpen = False
			try:
				return script(*args, **kwargs)
			finally:
				if not self._keepLayerOpen:
					self.finishInstantLayer()

		return wrappedScript

	def _getGesturesForScript(self, scriptDescription, fallback):
		return getAddonGestures(scriptDescription, fallback)

	def getToggleGestures(self):
		return self._getGesturesForScript(TOGGLE_DESCRIPTION, ADDON_SCRIPT_GESTURES[TOGGLE_DESCRIPTION])

	def getReportAppNameGestures(self):
		return self._getGesturesForScript(
			REPORT_APP_NAME_DESCRIPTION,
			ADDON_SCRIPT_GESTURES[REPORT_APP_NAME_DESCRIPTION],
		)

	def getCurrentAppName(self):
		try:
			focus = api.getFocusObject()
			appModule = getattr(focus, "appModule", None)
			appName = getattr(appModule, "appName", "")
			return (appName or "").strip().lower()
		except Exception as e:
			log.warning("instantAccess: Error getting current app name: %s", e)
			return ""

	def buildInstantGestures(self):
		items = [item for item in self.configManager.getItems() if item.get("enabled", True)]
		self.layerItems = items
		self.browseSettings = self.configManager.getSettings()
		self.gestureToItems = {}
		for item in items:
			for gesture in item.get("gestures", []):
				key = gestureKey(gesture)
				if key:
					self.gestureToItems.setdefault(key, []).append(item)
		self.loadedCommandCount = len(
			{item["name"] for itemsForGesture in self.gestureToItems.values() for item in itemsForGesture},
		)
		instantGestures = {}
		for gesture in self.gestureToItems.keys():
			instantGestures[gesture] = "runInstantItem"
		instantGestures.update(self.buildBrowseGestures())
		for gesture in self.getToggleGestures():
			instantGestures[gesture] = "toggleInstantMode"
		for gesture in self.getReportAppNameGestures():
			instantGestures[gesture] = "reportCurrentAppName"
		instantGestures["kb:escape"] = "exitInstantMode"
		return instantGestures

	def buildBrowseGestures(self):
		"""Bind browse keys that no item uses; items keep their keys and fall back to browsing."""
		self.browseGestureScripts = {}
		if not self.browseSettings.get("browseEnabled"):
			return {}
		for gesture, scriptName in BROWSE_GESTURES.items():
			self.browseGestureScripts[gestureKey(gesture)] = scriptName
		return {
			gesture: scriptName
			for gesture, scriptName in self.browseGestureScripts.items()
			if gesture not in self.gestureToItems
		}

	def _resetBrowseState(self):
		self.browseItems = None
		self.browseIndex = -1

	def activateInstantMode(self, speak=True):
		if not self._enabled:
			return
		self._resetBrowseState()
		instantGestures = self.buildInstantGestures()
		if self.loadedCommandCount <= 0:
			self.instantMode = False
			self.clearGestureBindings()
			bindings = {gesture: "toggleInstantMode" for gesture in self.getToggleGestures()}
			for gesture in self.getReportAppNameGestures():
				bindings[gesture] = "reportCurrentAppName"
			self.bindGestures(bindings)
			if speak:
				# Translators: Announced when instant Access mode is turned on but no items exist.
				ui.message(_("No commands configured."))
			return
		self.instantMode = True
		self.clearGestureBindings()
		self.bindGestures(instantGestures)
		if speak:
			if self.isAdvancedVerbosity():
				# Translators: Short announcement when instant Access mode turns on (advanced verbosity).
				ui.message(_("On"))
			else:
				# Items restricted to other apps cannot run here, so they are not counted.
				count = len(getUsableItems(self.layerItems, self.getCurrentAppName()))
				# Translators: Announced when instant Access mode turns on. {count} is the number of usable items.
				ui.message(_("instant Access On. {count} commands loaded").format(count=count))

	def deactivateInstantMode(self, speak=True):
		if not self.instantMode:
			return
		self.instantMode = False
		self._resetBrowseState()
		self.clearGestureBindings()
		bindings = {gesture: "toggleInstantMode" for gesture in self.getToggleGestures()}
		for gesture in self.getReportAppNameGestures():
			bindings[gesture] = "reportCurrentAppName"
		self.bindGestures(bindings)
		if speak:
			if self.isAdvancedVerbosity():
				# Translators: Short announcement when instant Access mode turns off (advanced verbosity).
				ui.message(_("Off"))
			else:
				# Translators: Announced when instant Access mode turns off.
				ui.message(_("instant Access Off"))

	def finishInstantLayer(self):
		if self.instantMode:
			self.deactivateInstantMode(speak=False)

	def script_invalidKey(self, gesture):
		if self.isAdvancedVerbosity():
			self.queueTone(250, 50)
			return
		# Translators: Announced when a key with no item is pressed in instant Access mode.
		ui.message(_("This gesture has no command assigned."))
		tones.beep(200, 50)

	@scriptHandler.script(
		category=CATEGORY_LABEL,
		description=TOGGLE_DESCRIPTION,
		gesture="kb:NVDA+e",
	)
	def script_toggleInstantMode(self, gesture):
		if not self._enabled:
			return
		if self.instantMode:
			self.deactivateInstantMode()
		else:
			self.activateInstantMode()

	def script_exitInstantMode(self, gesture):
		self.deactivateInstantMode()

	def script_runInstantItem(self, gesture):
		# NVDA's normalized identifiers, as used by ScriptableObject.getScript, keep modifier order stable.
		identifiers = list(getattr(gesture, "normalizedIdentifiers", None) or ())
		candidateItems = []
		for gestureId in identifiers:
			candidateItems.extend(self.gestureToItems.get(gestureId, []))
		item = resolveItem(candidateItems, self.getCurrentAppName())
		if item is None:
			# The key belongs to an item for another app; let it browse here if it is a browse key.
			self._runBrowseFallback(identifiers, gesture)
			return
		self.queueRunItemExecution(item)

	def _runBrowseFallback(self, identifiers, gesture):
		for gestureId in identifiers:
			scriptName = self.browseGestureScripts.get(gestureId)
			if scriptName:
				getattr(self, "script_" + scriptName)(gesture)
				return

	def getBrowseItems(self):
		if self.browseItems is None:
			usable = getUsableItems(self.layerItems, self.getCurrentAppName())
			self.browseItems = sortItems(usable, self.browseSettings.get("browseOrder"))
		return self.browseItems

	def moveBrowse(self, step):
		self._keepLayerOpen = True
		items = self.getBrowseItems()
		if not items:
			# Translators: Announced when browsing the layer but no item can run in the current application.
			ui.message(_("No items are available in this application."))
			return
		if self.browseIndex < 0:
			self.browseIndex = 0 if step > 0 else len(items) - 1
		else:
			self.browseIndex = (self.browseIndex + step) % len(items)
		ui.message(formatItem(items[self.browseIndex], self.browseSettings.get("browseFormat")))

	def script_browseNext(self, gesture):
		self.moveBrowse(1)

	def script_browsePrevious(self, gesture):
		self.moveBrowse(-1)

	def script_browseActivate(self, gesture):
		if self.browseIndex < 0 or not self.browseItems:
			self.script_invalidKey(gesture)
			return
		self.queueRunItemExecution(self.browseItems[self.browseIndex])

	def script_browseHelp(self, gesture):
		text = buildHelpText(self.getBrowseItems(), self.browseSettings.get("browseFormat"))
		# Translators: Title of the window listing instant Access items available in the current application.
		ui.browseableMessage(text, _("instant Access items"))

	@scriptHandler.script(
		category=CATEGORY_LABEL,
		description=REPORT_APP_NAME_DESCRIPTION,
		gesture="kb:NVDA+shift+e",
	)
	def script_reportCurrentAppName(self, gesture):
		if not self._enabled:
			return
		appName = self.getCurrentAppName()
		if not appName:
			# Translators: Message announced when current application name could not be determined.
			ui.message(_("Could not determine current application name."))
			return
		if scriptHandler.getLastScriptRepeatCount() > 0:
			if setClipboardText(appName):
				# Translators: Message announced after the current app name was copied to the clipboard.
				ui.message(_("App name copied to clipboard."))
			return
		ui.message(appName)
