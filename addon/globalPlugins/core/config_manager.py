# -*- coding: utf-8 -*-

from logHandler import log
from .config_io import ensureConfigFile, loadConfigSafe, loadConfigFromPathStrict, saveConfig
from .constants import ACTION_FIELDS, ANNOUNCE_VALUES, DEFAULT_SETTINGS, VERBOSITY_VALUES
from .gestures import appNamesConflict, gestureKey



class ConfigManager:
	"""Manages the configuration for the instantAccess add-on."""

	def __init__(self, configPath):
		"""Initialize the ConfigManager with a configuration file path."""
		self.configPath = configPath
		self._cachedConfig = None
		ensureConfigFile(self.configPath)

	def loadOrCreateConfig(self):
		"""The normalized config, read from disk once and kept until the next save or import.

		NVDA+E rebuilds the layer from it, so the file is not read on every key press, and the
		backup recovery question is asked at most once per session. Callers must not modify it.
		"""
		if self._cachedConfig is None:
			self._cachedConfig = loadConfigSafe(self.configPath)
		return self._cachedConfig

	def saveConfig(self, config):
		"""Save the configuration to file."""
		try:
			saveConfig(self.configPath, config)
		finally:
			self._cachedConfig = None

	def replaceConfig(self, config):
		"""Replace the whole configuration, as an import does."""
		self.saveConfig(config)

	def _loadConfigForUpdate(self):
		"""Do not turn a read-only recovery fallback into a destructive write."""
		return loadConfigFromPathStrict(self.configPath)

	def getConfigPath(self):
		"""Get the path to the configuration file."""
		return self.configPath

	def _actionToPublic(self, storedAction):
		"""Stored actions are already normalized; the dialogs call each type's main value "path"."""
		itemType = storedAction["type"]
		data = storedAction["data"]
		return {
			"type": itemType,
			"path": data[ACTION_FIELDS[itemType]],
			"arguments": data.get("arguments", ""),
			"runAsAdmin": data.get("runAsAdmin", False),
			"textAction": data.get("action", "type"),
			"typingDelay": data.get("typingDelay", 0.05),
			"commandLabel": data.get("commandLabel", ""),
			"pressDelay": data.get("pressDelay", 0.05),
			"delay": storedAction.get("delay", 0.0),
		}

	def _toPublicItem(self, storedItem):
		gesture = storedItem["gesture"]
		return {
			"name": storedItem["name"],
			"appName": storedItem.get("appName", ""),
			"interval": storedItem.get("interval", 0.0),
			"stopOnError": storedItem.get("stopOnError", True),
			"enabled": storedItem.get("enabled", True),
			"announceName": storedItem.get("announceName", ANNOUNCE_VALUES[0]),
			"actions": [self._actionToPublic(action) for action in storedItem["actions"]],
			"gestures": [gesture] if gesture else [],
		}

	def _buildStoredAction(self, action):
		"""Invalid values are left to saveConfig, which rejects them with ValueError."""
		itemType = action.get("type", "")
		if itemType not in ACTION_FIELDS:
			raise ValueError(f"Invalid action type: {itemType!r}")
		data = {ACTION_FIELDS[itemType]: action.get("path", "")}
		if itemType == "Programs":
			data["arguments"] = action.get("arguments", "")
			data["runAsAdmin"] = bool(action.get("runAsAdmin", False))
		elif itemType == "NvdaCommands":
			data["commandLabel"] = action.get("commandLabel", "")
		elif itemType == "TextSnippets":
			data["action"] = (action.get("textAction", "type") or "").strip().lower()
			data["typingDelay"] = action.get("typingDelay", 0.05)
		elif itemType == "Keystrokes":
			data["pressDelay"] = action.get("pressDelay", 0.05)
		return {"type": itemType, "data": data, "delay": action.get("delay", 0.0)}

	def _buildStoredItem(
		self,
		name,
		gesture,
		actions,
		interval=0.0,
		appName="",
		stopOnError=True,
		enabled=True,
		announceName=ANNOUNCE_VALUES[0],
	):
		item = {
			"name": name,
			"gesture": (gesture or "").strip().lower(),
			"interval": interval,
			"stopOnError": bool(stopOnError),
			"enabled": bool(enabled),
			"announceName": announceName,
			"actions": [self._buildStoredAction(action) for action in actions],
		}
		if (appName or "").strip():
			item["appName"] = appName
		return item

	def getItems(self):
		"""Get all configured items."""
		config = self.loadOrCreateConfig()
		items = []
		for storedItem in config.get("items", []):
			try:
				items.append(self._toPublicItem(storedItem))
			except Exception as e:
				log.error("instantAccess: Error converting item to public format: %s", e)
		return items

	def getAllNames(self):
		"""Get all configured item names."""
		return {item.get("name", "") for item in self.getItems()}

	def findGestureConflict(self, gesture, appName="", excludeName=""):
		"""Find if a gesture conflicts with an existing item."""
		normalizedGesture = gestureKey(gesture)
		if not normalizedGesture:
			return None
		for item in self.getItems():
			if excludeName and item.get("name", "") == excludeName:
				continue
			for itemGesture in item.get("gestures", []):
				if gestureKey(itemGesture) != normalizedGesture:
					continue
				if appNamesConflict(item.get("appName", ""), appName):
					return item
		return None

	def getUniqueItemName(self, baseName):
		"""Generate a unique item name for duplicating an item."""
		existingNames = self.getAllNames()
		candidate = f"{baseName} (copy)"
		if candidate not in existingNames:
			return candidate
		for counter in range(2, len(existingNames) + 3):
			candidate = f"{baseName} (copy {counter})"
			if candidate not in existingNames:
				return candidate
		return candidate

	def saveItem(
		self,
		oldName,
		name,
		gesture,
		actions,
		interval=0.0,
		appName="",
		stopOnError=True,
		enabled=True,
		announceName=ANNOUNCE_VALUES[0],
	):
		"""Add an item, or replace oldName at its place; browsing follows the settings order."""
		config = self._loadConfigForUpdate()
		newItem = self._buildStoredItem(
			name=name,
			gesture=gesture,
			actions=actions,
			interval=interval,
			appName=appName,
			stopOnError=stopOnError,
			enabled=enabled,
			announceName=announceName,
		)
		items = []
		replaced = False
		for item in config.get("items", []):
			itemName = item.get("name", "")
			if oldName and itemName == oldName and not replaced:
				items.append(newItem)
				replaced = True
			elif itemName not in (oldName, name):
				items.append(item)
		if not replaced:
			items.append(newItem)
		config["items"] = items
		self.saveConfig(config)

	def mergeItems(self, imported):
		"""Add imported items with a new name and a free shortcut; settings stay. Returns (added, skipped)."""
		# Imported items cannot clash with each other: the file passed validation.
		names = self.getAllNames()
		newItems = [
			item
			for item in imported.get("items", [])
			if item["name"] not in names
			and not self.findGestureConflict(item["gesture"], item.get("appName", ""))
		]
		if newItems:
			config = self._loadConfigForUpdate()
			config["items"] = config.get("items", []) + newItems
			self.saveConfig(config)
		return len(newItems), len(imported.get("items", [])) - len(newItems)

	def moveItem(self, name, step):
		"""Swap an item with its neighbour; False when it cannot move that way."""
		config = self._loadConfigForUpdate()
		items = config.get("items", [])
		names = [item.get("name", "") for item in items]
		if name not in names:
			return False
		index = names.index(name)
		target = index + step
		if not 0 <= target < len(items):
			return False
		items[index], items[target] = items[target], items[index]
		self.saveConfig(config)
		return True

	def deleteItem(self, name):
		"""Delete an item from the configuration."""
		config = self._loadConfigForUpdate()
		config["items"] = [item for item in config.get("items", []) if item.get("name", "") != name]
		self.saveConfig(config)

	def getVerbosityLevel(self):
		"""Get the current verbosity level setting."""
		config = self.loadOrCreateConfig()
		settings = config.get("settings", {})
		value = (settings.get("verbosity", VERBOSITY_VALUES[0]) or "").strip().lower()
		if value not in VERBOSITY_VALUES:
			value = VERBOSITY_VALUES[0]
		return value

	def getSettings(self):
		"""Get all settings, with defaults filled in."""
		settings = dict(DEFAULT_SETTINGS)
		settings.update(self.loadOrCreateConfig().get("settings", {}))
		return settings

	def updateSettings(self, **values):
		"""Save several settings in one write; unknown keys are rejected."""
		unknown = set(values) - set(DEFAULT_SETTINGS)
		if unknown:
			raise ValueError(f"Unknown settings: {sorted(unknown)}")
		config = self._loadConfigForUpdate()
		config.setdefault("settings", {}).update(values)
		self.saveConfig(config)
