# -*- coding: utf-8 -*-

from .config_io import ensureConfigFile, loadConfigSafe, saveConfig
from .constants import TYPE_SECTIONS, VERBOSITY_VALUES


class ConfigManager:
	def __init__(self, configPath):
		self.configPath = configPath
		ensureConfigFile(self.configPath)

	def loadOrCreateConfig(self):
		return loadConfigSafe(self.configPath)

	def saveConfig(self, config):
		saveConfig(self.configPath, config)

	def getConfigPath(self):
		return self.configPath

	def _actionToPublic(self, storedAction):
		itemType = storedAction.get("type", "")
		data = storedAction.get("data", {})
		if not isinstance(data, dict):
			data = {}
		path = ""
		arguments = ""
		textAction = "type"
		typingDelay = 0.05
		commandLabel = ""
		if itemType == "Websites":
			path = data.get("url", "")
		elif itemType in ("Programs", "Folders", "Files"):
			path = data.get("path", "")
			if itemType == "Programs":
				arguments = data.get("arguments", "")
		elif itemType == "NvdaCommands":
			path = data.get("commandId", "")
			commandLabel = data.get("commandLabel", "")
		elif itemType == "TextSnippets":
			path = data.get("text", "")
			textAction = data.get("action", "type")
			try:
				typingDelay = float(data.get("typingDelay", 0.05) or 0.05)
			except Exception:
				typingDelay = 0.05
			if typingDelay < 0:
				typingDelay = 0.05
		return {
			"type": itemType,
			"path": path if isinstance(path, str) else "",
			"arguments": arguments if isinstance(arguments, str) else "",
			"textAction": textAction if isinstance(textAction, str) else "type",
			"typingDelay": typingDelay,
			"commandLabel": commandLabel if isinstance(commandLabel, str) else "",
			"delay": float(storedAction.get("delay", 0.0) or 0.0),
		}

	def _toPublicItem(self, storedItem):
		actions = [self._actionToPublic(action) for action in storedItem.get("actions", [])]
		gesture = (storedItem.get("gesture", "") or "").strip().lower()
		return {
			"name": storedItem.get("name", ""),
			"appName": (storedItem.get("appName", "") or "").strip().lower(),
			"interval": float(storedItem.get("interval", 0.0) or 0.0),
			"actions": actions,
			"gestures": [gesture] if gesture else [],
		}

	def _buildStoredAction(self, action):
		itemType = action.get("type", "")
		if itemType not in TYPE_SECTIONS:
			itemType = TYPE_SECTIONS[0]
		delay = action.get("delay", 0.0)
		try:
			delay = float(delay)
		except Exception:
			delay = 0.0
		if delay < 0:
			delay = 0.0
		if itemType == "Websites":
			data = {"url": action.get("path", "")}
		elif itemType in ("Programs", "Folders", "Files"):
			data = {"path": action.get("path", "")}
			if itemType == "Programs" and (action.get("arguments", "") or "").strip():
				data["arguments"] = action.get("arguments", "").strip()
		elif itemType == "NvdaCommands":
			data = {"commandId": action.get("path", "")}
			if (action.get("commandLabel", "") or "").strip():
				data["commandLabel"] = action.get("commandLabel", "").strip()
		else:
			try:
				typingDelay = float(action.get("typingDelay", 0.05) or 0.05)
			except Exception:
				typingDelay = 0.05
			if typingDelay < 0:
				typingDelay = 0.05
			data = {
				"text": action.get("path", ""),
				"action": (action.get("textAction", "type") or "").strip().lower(),
				"typingDelay": typingDelay,
			}
		return {"type": itemType, "data": data, "delay": delay}

	def _buildStoredItem(self, name, gesture, actions, interval=0.0, appName=""):
		try:
			interval = float(interval)
		except Exception:
			interval = 0.0
		if interval < 0:
			interval = 0.0
		storedActions = [self._buildStoredAction(action) for action in actions]
		item = {
			"name": name,
			"gesture": (gesture or "").strip().lower(),
			"interval": interval,
			"actions": storedActions,
		}
		normalizedAppName = (appName or "").strip().lower()
		if normalizedAppName:
			item["appName"] = normalizedAppName
		return item

	def getItems(self):
		config = self.loadOrCreateConfig()
		items = []
		for storedItem in config.get("items", []):
			items.append(self._toPublicItem(storedItem))
		return items

	def getAllNames(self):
		return {item.get("name", "") for item in self.getItems()}

	def getGestureToNameMap(self):
		gestureMap = {}
		for item in self.getItems():
			name = item.get("name", "")
			for gesture in item.get("gestures", []):
				normalized = (gesture or "").strip().lower()
				if normalized and normalized not in gestureMap:
					gestureMap[normalized] = name
		return gestureMap

	def findGestureConflict(self, gesture, appName="", excludeName=""):
		normalizedGesture = (gesture or "").strip().lower()
		normalizedAppName = (appName or "").strip().lower()
		if not normalizedGesture:
			return None
		for item in self.getItems():
			if excludeName and item.get("name", "") == excludeName:
				continue
			itemAppName = (item.get("appName", "") or "").strip().lower()
			for itemGesture in item.get("gestures", []):
				if (itemGesture or "").strip().lower() != normalizedGesture:
					continue
				if itemAppName == normalizedAppName:
					return item
		return None

	def addItem(self, name, gesture, actions, interval=0.0, appName=""):
		config = self.loadOrCreateConfig()
		items = [item for item in config.get("items", []) if item.get("name", "") != name]
		items.append(self._buildStoredItem(name=name, gesture=gesture, actions=actions, interval=interval, appName=appName))
		config["items"] = items
		self.saveConfig(config)

	def updateItem(self, oldName, name, gesture, actions, interval=0.0, appName=""):
		config = self.loadOrCreateConfig()
		items = [item for item in config.get("items", []) if item.get("name", "") not in (oldName, name)]
		items.append(self._buildStoredItem(name=name, gesture=gesture, actions=actions, interval=interval, appName=appName))
		config["items"] = items
		self.saveConfig(config)

	def deleteItem(self, name):
		config = self.loadOrCreateConfig()
		config["items"] = [item for item in config.get("items", []) if item.get("name", "") != name]
		self.saveConfig(config)

	def getVerbosityLevel(self):
		config = self.loadOrCreateConfig()
		settings = config.get("settings", {})
		value = (settings.get("verbosity", VERBOSITY_VALUES[0]) or "").strip().lower()
		if value not in VERBOSITY_VALUES:
			value = VERBOSITY_VALUES[0]
		return value

	def setVerbosityLevel(self, value):
		config = self.loadOrCreateConfig()
		value = (value or "").strip().lower()
		if value not in VERBOSITY_VALUES:
			value = VERBOSITY_VALUES[0]
		config.setdefault("settings", {})
		config["settings"]["verbosity"] = value
		self.saveConfig(config)
