# -*- coding: utf-8 -*-

from concurrent.futures import ThreadPoolExecutor
import os

import api
import globalPluginHandler
import globalVars
import gui
import inputCore
import scriptHandler
import tones
import ui
import wx

from .config_manager import ConfigManager
from .constants import CATEGORY_LABEL, REPORT_APP_NAME_DESCRIPTION, TOGGLE_DESCRIPTION, VERBOSITY_VALUES
from .executor import executeInstantItem
from .gestures import expandGestureLayouts, normalizeGestureIdentifier
from .settings_panel import InstantAccessSettingsPanel


def wrapFinally(func, final):
	def wrapped(*args, **kwargs):
		try:
			return func(*args, **kwargs)
		finally:
			final()

	return wrapped


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self):
		super().__init__()
		if globalVars.appArgs.secure:
			return
		self.executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="instantAccess")
		self.verbosityLevel = VERBOSITY_VALUES[0]
		self.instantMode = False
		self.gestureToItems = {}
		self.loadedCommandCount = 0
		configPath = os.path.join(globalVars.appArgs.configPath, "instantAccess", "config.json")
		self.configManager = ConfigManager(configPath)
		self.setVerbosityLevel(self.configManager.getVerbosityLevel())
		InstantAccessSettingsPanel.configManager = self.configManager
		InstantAccessSettingsPanel.onConfigChanged = self.onConfigChanged
		InstantAccessSettingsPanel.onRunItem = self.queueRunItemExecution
		InstantAccessSettingsPanel.onVerbosityChanged = self.setVerbosityLevel
		gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(InstantAccessSettingsPanel)

	def terminate(self):
		if not hasattr(self, "executor"):
			return
		try:
			gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(InstantAccessSettingsPanel)
		except Exception:
			pass
		InstantAccessSettingsPanel.onRunItem = None
		InstantAccessSettingsPanel.onVerbosityChanged = None
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
			textAction=item.get("textAction", "type"),
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

	def getReportAppNameGestures(self):
		try:
			mappings = inputCore.manager.getAllGestureMappings()
			categoryMap = mappings.get(CATEGORY_LABEL, {})
			scriptInfo = categoryMap.get(REPORT_APP_NAME_DESCRIPTION)
			if scriptInfo and getattr(scriptInfo, "gestures", None):
				return list(scriptInfo.gestures)
		except Exception:
			pass
		return ["kb:NVDA+shift+e"]

	def getCurrentAppName(self):
		try:
			focus = api.getFocusObject()
			appModule = getattr(focus, "appModule", None)
			appName = getattr(appModule, "appName", "")
			return (appName or "").strip().lower()
		except Exception:
			return ""

	def buildInstantGestures(self):
		items = self.configManager.getItems()
		self.gestureToItems = {}
		for item in items:
			for gesture in item.get("gestures", []):
				for expanded in expandGestureLayouts(gesture):
					self.gestureToItems.setdefault(expanded.lower(), []).append(item)
		self.loadedCommandCount = len({item["name"] for itemsForGesture in self.gestureToItems.values() for item in itemsForGesture})
		instantGestures = {}
		for gesture in self.gestureToItems.keys():
			instantGestures[gesture] = "runInstantItem"
		for gesture in self.getToggleGestures():
			instantGestures[gesture] = "toggleInstantMode"
		for gesture in self.getReportAppNameGestures():
			instantGestures[gesture] = "reportCurrentAppName"
		instantGestures["kb:escape"] = "exitInstantMode"
		return instantGestures

	def activateInstantMode(self, speak=True):
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
		if not candidateItems:
			return
		currentAppName = self.getCurrentAppName()
		item = None
		for candidate in candidateItems:
			itemAppName = (candidate.get("appName", "") or "").strip().lower()
			if itemAppName and itemAppName == currentAppName:
				item = candidate
				break
		if item is None:
			for candidate in candidateItems:
				if not (candidate.get("appName", "") or "").strip():
					item = candidate
					break
		if item is None:
			return
		self.queueRunItemExecution(item)

	@scriptHandler.script(
		category=CATEGORY_LABEL,
		description=REPORT_APP_NAME_DESCRIPTION,
		gesture="kb:NVDA+shift+e",
	)
	def script_reportCurrentAppName(self, gesture):
		appName = self.getCurrentAppName()
		if not appName:
			return
		if scriptHandler.getLastScriptRepeatCount() > 0:
			if hasattr(api, "setClipText"):
				api.setClipText(appName)
			elif hasattr(api, "copyToClip"):
				api.copyToClip(appName, notify=False)
			ui.message(_("App name copied to clipboard."))
			return
		ui.message(appName)
