# -*- coding: utf-8 -*-

from .config_io import ensureConfigFile, loadConfigSafe, saveConfig
from .constants import CONFIG_SECTIONS, TYPE_SECTIONS, VERBOSITY_VALUES


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

	def _removeOptionIfSectionExists(self, config, section, name):
		if config.has_section(section):
			config.remove_option(section, name)

	def getItems(self):
		config = self.loadOrCreateConfig()
		gestureMap = {}
		argumentMap = {}
		textActionMap = {}
		commandLabelMap = {}
		if config.has_section("Gestures"):
			for gesture, name in config.items("Gestures"):
				gestureMap.setdefault(name, []).append(gesture)
		if config.has_section("Arguments"):
			for name, argumentText in config.items("Arguments"):
				argumentMap[name] = argumentText
		if config.has_section("TextSnippetActions"):
			for name, action in config.items("TextSnippetActions"):
				textActionMap[name] = action
		if config.has_section("CommandLabels"):
			for name, label in config.items("CommandLabels"):
				commandLabelMap[name] = label
		items = []
		for section in TYPE_SECTIONS:
			if not config.has_section(section):
				continue
			for name, path in config.items(section):
				items.append(
					{
						"name": name,
						"type": section,
						"path": path,
						"arguments": argumentMap.get(name, ""),
						"textAction": textActionMap.get(name, "type"),
						"commandLabel": commandLabelMap.get(name, ""),
						"gestures": gestureMap.get(name, []),
					},
				)
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

	def addItem(self, name, itemType, path, gesture, arguments="", textAction="type", commandLabel=""):
		config = self.loadOrCreateConfig()
		if not config.has_section(itemType):
			config.add_section(itemType)
		config.set(itemType, name, path)
		self.removeGesturesForName(config, name)

		self._removeOptionIfSectionExists(config, "Arguments", name)
		self._removeOptionIfSectionExists(config, "TextSnippetActions", name)
		self._removeOptionIfSectionExists(config, "CommandLabels", name)

		if itemType == "Programs" and arguments.strip():
			config.set("Arguments", name, arguments.strip())
		if itemType == "TextSnippets":
			config.set("TextSnippetActions", name, (textAction or "type").strip().lower())
		if itemType == "NvdaCommands" and commandLabel.strip():
			config.set("CommandLabels", name, commandLabel.strip())
		if gesture:
			config.set("Gestures", gesture, name)
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
	):
		config = self.loadOrCreateConfig()
		for section in TYPE_SECTIONS:
			if config.has_section(section) and config.has_option(section, oldName):
				config.remove_option(section, oldName)
		if not config.has_section(itemType):
			config.add_section(itemType)
		config.set(itemType, name, path)

		for section in ("Arguments", "TextSnippetActions", "CommandLabels"):
			self._removeOptionIfSectionExists(config, section, oldName)
			self._removeOptionIfSectionExists(config, section, name)

		if itemType == "Programs" and arguments.strip():
			config.set("Arguments", name, arguments.strip())
		if itemType == "TextSnippets":
			config.set("TextSnippetActions", name, (textAction or "type").strip().lower())
		if itemType == "NvdaCommands" and commandLabel.strip():
			config.set("CommandLabels", name, commandLabel.strip())

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
		for section in ("Arguments", "TextSnippetActions", "CommandLabels"):
			self._removeOptionIfSectionExists(config, section, name)
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
