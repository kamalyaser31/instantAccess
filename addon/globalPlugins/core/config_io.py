# -*- coding: utf-8 -*-

import copy
import json
import os

from .constants import TEXT_SNIPPET_ACTION_VALUES, TYPE_SECTIONS, VERBOSITY_VALUES


def _defaultConfig():
	return {
		"version": 3,
		"settings": {"verbosity": VERBOSITY_VALUES[0]},
		"items": [],
	}


def _toNonNegativeFloat(value, defaultValue=0.0):
	try:
		number = float(value)
		if number < 0:
			return defaultValue
		return number
	except Exception:
		return defaultValue


def _normalizeActionData(itemType, rawData):
	if not isinstance(rawData, dict):
		rawData = {}
	if itemType == "Websites":
		url = rawData.get("url", "")
		if not isinstance(url, str):
			url = ""
		return {"url": url}
	if itemType in ("Programs", "Folders", "Files"):
		path = rawData.get("path", "")
		if not isinstance(path, str):
			path = ""
		data = {"path": path}
		if itemType == "Programs":
			arguments = rawData.get("arguments", "")
			if isinstance(arguments, str) and arguments.strip():
				data["arguments"] = arguments.strip()
		return data
	if itemType == "NvdaCommands":
		commandId = rawData.get("commandId", "")
		if not isinstance(commandId, str):
			commandId = ""
		data = {"commandId": commandId}
		commandLabel = rawData.get("commandLabel", "")
		if isinstance(commandLabel, str) and commandLabel.strip():
			data["commandLabel"] = commandLabel.strip()
		return data
	if itemType == "TextSnippets":
		text = rawData.get("text", "")
		if not isinstance(text, str):
			text = ""
		action = (rawData.get("action", TEXT_SNIPPET_ACTION_VALUES[0]) or "").strip().lower()
		if action not in TEXT_SNIPPET_ACTION_VALUES:
			action = TEXT_SNIPPET_ACTION_VALUES[0]
		typingDelay = _toNonNegativeFloat(rawData.get("typingDelay", 0.05), 0.05)
		return {"text": text, "action": action, "typingDelay": typingDelay}
	return {}


def _normalizeAction(rawAction):
	if not isinstance(rawAction, dict):
		return None
	itemType = (rawAction.get("type", "") or "").strip()
	if itemType not in TYPE_SECTIONS:
		return None
	delay = _toNonNegativeFloat(rawAction.get("delay", 0.0), 0.0)
	data = _normalizeActionData(itemType, rawAction.get("data", {}))
	return {"type": itemType, "data": data, "delay": delay}


def _normalizeItem(rawItem):
	if not isinstance(rawItem, dict):
		return None
	name = (rawItem.get("name", "") or "").strip()
	gesture = (rawItem.get("gesture", "") or "").strip().lower()
	appName = (rawItem.get("appName", "") or "").strip().lower()
	interval = _toNonNegativeFloat(rawItem.get("interval", 0.0), 0.0)
	if not name or not gesture:
		return None
	rawActions = rawItem.get("actions", [])
	if not isinstance(rawActions, list):
		rawActions = []
	actions = []
	for rawAction in rawActions:
		action = _normalizeAction(rawAction)
		if action is not None:
			actions.append(action)
	normalizedItem = {
		"name": name,
		"gesture": gesture,
		"interval": interval,
		"actions": actions,
	}
	if appName:
		normalizedItem["appName"] = appName
	return normalizedItem


def _normalizeConfig(rawConfig):
	if not isinstance(rawConfig, dict):
		raise ValueError("Invalid config format")
	settings = rawConfig.get("settings", {})
	if not isinstance(settings, dict):
		settings = {}
	verbosity = (settings.get("verbosity", VERBOSITY_VALUES[0]) or "").strip().lower()
	if verbosity not in VERBOSITY_VALUES:
		verbosity = VERBOSITY_VALUES[0]
	rawItems = rawConfig.get("items", [])
	if not isinstance(rawItems, list):
		rawItems = []
	items = []
	for rawItem in rawItems:
		item = _normalizeItem(rawItem)
		if item is not None:
			items.append(item)
	return {"version": 3, "settings": {"verbosity": verbosity}, "items": items}


def ensureConfigFile(configPath):
	configDir = os.path.dirname(configPath)
	os.makedirs(configDir, exist_ok=True)
	if not os.path.exists(configPath):
		saveConfig(configPath, _defaultConfig())


def saveConfig(configPath, config):
	configDir = os.path.dirname(configPath)
	os.makedirs(configDir, exist_ok=True)
	normalized = _normalizeConfig(config)
	with open(configPath, "w", encoding="utf-8") as handle:
		json.dump(normalized, handle, ensure_ascii=False, indent="\t")


def loadConfigSafe(configPath):
	ensureConfigFile(configPath)
	try:
		with open(configPath, "r", encoding="utf-8") as handle:
			rawConfig = json.load(handle)
		return _normalizeConfig(rawConfig)
	except Exception:
		defaultConfig = _defaultConfig()
		saveConfig(configPath, defaultConfig)
		return copy.deepcopy(defaultConfig)


def loadConfigFromPathStrict(configPath):
	with open(configPath, "r", encoding="utf-8") as handle:
		rawConfig = json.load(handle)
	return _normalizeConfig(rawConfig)
