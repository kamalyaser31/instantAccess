# -*- coding: utf-8 -*-

from concurrent.futures import ThreadPoolExecutor
import os

import globalPluginHandler
import globalVars
import gui
import inputCore
import scriptHandler
import tones
import ui
import wx

from .config_manager import ConfigManager
from .constants import CATEGORY_LABEL, TOGGLE_DESCRIPTION, VERBOSITY_VALUES
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
		self.gestureToItem = {}
		self.loadedCommandCount = 0
		configPath = os.path.join(globalVars.appArgs.configPath, "instantAccess", "config.ini")
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
		self.bindGestures({gesture: "toggleInstantMode" for gesture in self.getToggleGestures()})
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
		item = None
		for gestureId in identifiers:
			normalized = normalizeGestureIdentifier(gestureId)
			item = self.gestureToItem.get(normalized)
			if item:
				break
		if not item:
			return
		self.queueRunItemExecution(item)
