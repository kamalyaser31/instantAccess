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

	def _buildStoredItem(self, name, itemType, path, gesture, arguments="", textAction="type", commandLabel="", appName=""):
		normalizedType = itemType if itemType in TYPE_SECTIONS else TYPE_SECTIONS[0]
		data = {}
		if normalizedType == "Websites":
			data["url"] = path
		elif normalizedType in ("Programs", "Folders", "Files"):
			data["path"] = path
			if normalizedType == "Programs" and arguments.strip():
				data["arguments"] = arguments.strip()
		elif normalizedType == "NvdaCommands":
			data["commandId"] = path
			if commandLabel.strip():
				data["commandLabel"] = commandLabel.strip()
		elif normalizedType == "TextSnippets":
			data["text"] = path
			data["action"] = (textAction or "type").strip().lower()

		item = {
			"name": name,
			"type": normalizedType,
			"gesture": (gesture or "").strip().lower(),
			"data": data,
		}
		normalizedAppName = (appName or "").strip().lower()
		if normalizedAppName:
			item["appName"] = normalizedAppName
		return item

	def _toPublicItem(self, storedItem):
		itemType = storedItem.get("type", "")
		data = storedItem.get("data", {})
		if not isinstance(data, dict):
			data = {}
		path = ""
		arguments = ""
		textAction = "type"
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
		return {
			"name": storedItem.get("name", ""),
			"type": itemType,
			"path": path if isinstance(path, str) else "",
			"arguments": arguments if isinstance(arguments, str) else "",
			"textAction": textAction if isinstance(textAction, str) else "type",
			"commandLabel": commandLabel if isinstance(commandLabel, str) else "",
			"appName": (storedItem.get("appName", "") or "").strip().lower(),
			"gestures": [storedItem.get("gesture", "")] if storedItem.get("gesture", "") else [],
		}

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

	def addItem(self, name, itemType, path, gesture, arguments="", textAction="type", commandLabel="", appName=""):
		config = self.loadOrCreateConfig()
		items = config.get("items", [])
		items = [item for item in items if item.get("name", "") != name]
		items.append(self._buildStoredItem(name, itemType, path, gesture, arguments, textAction, commandLabel, appName))
		config["items"] = items
		self.saveConfig(config)

	def updateItem(
		self,
		oldName,
		name,
		itemType,
		path,
		gesture,
		arguments="",
		textAction="type",
		commandLabel="",
		appName="",
	):
		config = self.loadOrCreateConfig()
		items = [item for item in config.get("items", []) if item.get("name", "") not in (oldName, name)]
		items.append(self._buildStoredItem(name, itemType, path, gesture, arguments, textAction, commandLabel, appName))
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
