# -*- coding: utf-8 -*-

import logging
import os

import addonHandler
import api
import globalPluginHandler
import globalVars
import gui
import inputCore
import scriptHandler
import tones
import ui
import wx

from .browse import buildHelpText, formatItem, getUsableItems, resolveItem, sortItems
from .config_manager import ConfigManager
from .constants import (
	BROWSE_GESTURES,
	CATEGORY_LABEL,
	DEFAULT_SETTINGS,
	REPORT_APP_NAME_DESCRIPTION,
	TOGGLE_DESCRIPTION,
	VERBOSITY_VALUES,
)
from .executor import ExecutionQueue
from .gestures import expandGestureLayouts, normalizeGestureIdentifier
from .settings_panel import InstantAccessSettingsPanel

addonHandler.initTranslation()

log = logging.getLogger(__name__)


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
			log.error("Error removing settings panel during termination: %s", e, exc_info=True)

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

	def queueRunItemExecution(self, item):
		if not item or not self._enabled:
			return
		return self.executionQueue.submit(item)

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
		"""Return the gesture list bound to scriptDescription, or fallback if not found.

		Reads gesture mappings at call time so changes via Input Gestures dialog are reflected immediately.
		"""
		try:
			categoryMap = inputCore.manager.getAllGestureMappings().get(CATEGORY_LABEL, {})
			scriptInfo = categoryMap.get(scriptDescription)
			if scriptInfo and getattr(scriptInfo, "gestures", None):
				return list(scriptInfo.gestures)
		except KeyError:
			pass
		except Exception as e:
			log.warning("Error retrieving gestures for '%s': %s", scriptDescription, e)
		return fallback

	def getToggleGestures(self):
		return self._getGesturesForScript(TOGGLE_DESCRIPTION, ["kb:NVDA+e"])

	def getReportAppNameGestures(self):
		return self._getGesturesForScript(REPORT_APP_NAME_DESCRIPTION, ["kb:NVDA+shift+e"])

	def getCurrentAppName(self):
		try:
			focus = api.getFocusObject()
			appModule = getattr(focus, "appModule", None)
			appName = getattr(appModule, "appName", "")
			return (appName or "").strip().lower()
		except Exception as e:
			log.warning("Error getting current app name: %s", e)
			return ""

	def buildInstantGestures(self):
		items = self.configManager.getItems()
		self.layerItems = items
		self.browseSettings = self.configManager.getSettings()
		self.gestureToItems = {}
		for item in items:
			for gesture in item.get("gestures", []):
				for expanded in expandGestureLayouts(gesture):
					self.gestureToItems.setdefault(expanded.lower(), []).append(item)
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
			for expanded in expandGestureLayouts(gesture):
				self.browseGestureScripts[expanded.lower()] = scriptName
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
				ui.message(_("No commands configured."))
			return
		self.instantMode = True
		self.clearGestureBindings()
		self.bindGestures(instantGestures)
		if speak:
			if self.isAdvancedVerbosity():
				ui.message(_("On"))
			else:
				count = self.loadedCommandCount
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
				ui.message(_("Off"))
			else:
				ui.message(_("instant Access Off"))

	def finishInstantLayer(self):
		if self.instantMode:
			self.deactivateInstantMode(speak=False)

	def script_invalidKey(self, gesture):
		if self.isAdvancedVerbosity():
			self.queueTone(250, 50)
			return
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
		identifiers = []
		if hasattr(gesture, "identifiers") and gesture.identifiers:
			identifiers.extend(gesture.identifiers)
		elif hasattr(gesture, "identifier"):
			identifiers.append(gesture.identifier)
		candidateItems = []
		for gestureId in identifiers:
			normalized = normalizeGestureIdentifier(gestureId)
			items = self.gestureToItems.get(normalized, [])
			if items:
				candidateItems.extend(items)
		item = resolveItem(candidateItems, self.getCurrentAppName())
		if item is None:
			# The key belongs to an item for another app; let it browse here if it is a browse key.
			self._runBrowseFallback(identifiers, gesture)
			return
		self.queueRunItemExecution(item)

	def _runBrowseFallback(self, identifiers, gesture):
		for gestureId in identifiers:
			scriptName = self.browseGestureScripts.get(normalizeGestureIdentifier(gestureId))
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
			if hasattr(api, "setClipText"):
				api.setClipText(appName)
			elif hasattr(api, "copyToClip"):
				api.copyToClip(appName, notify=False)
			ui.message(_("App name copied to clipboard."))
			return
		ui.message(appName)
