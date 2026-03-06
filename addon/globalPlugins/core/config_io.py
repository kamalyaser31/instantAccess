# -*- coding: utf-8 -*-

import copy
import json
import os

from .constants import TEXT_SNIPPET_ACTION_VALUES, TYPE_SECTIONS, VERBOSITY_VALUES


def _defaultConfig():
	return {
		"version": 2,
		"settings": {"verbosity": VERBOSITY_VALUES[0]},
		"items": [],
	}


def _normalizeItem(rawItem):
	if not isinstance(rawItem, dict):
		return None
	name = (rawItem.get("name", "") or "").strip()
	itemType = (rawItem.get("type", "") or "").strip()
	gesture = (rawItem.get("gesture", "") or "").strip().lower()
	appName = (rawItem.get("appName", "") or "").strip().lower()
	data = rawItem.get("data", {})
	if itemType not in TYPE_SECTIONS:
		return None
	if not name or not gesture:
		return None
	if not isinstance(data, dict):
		data = {}

	normalizedData = {}
	if itemType == "Websites":
		url = data.get("url", "")
		if not isinstance(url, str):
			url = ""
		normalizedData["url"] = url
	elif itemType in ("Programs", "Folders", "Files"):
		path = data.get("path", "")
		if not isinstance(path, str):
			path = ""
		normalizedData["path"] = path
		if itemType == "Programs":
			arguments = data.get("arguments", "")
			if isinstance(arguments, str) and arguments.strip():
				normalizedData["arguments"] = arguments.strip()
	elif itemType == "NvdaCommands":
		commandId = data.get("commandId", "")
		if not isinstance(commandId, str):
			commandId = ""
		normalizedData["commandId"] = commandId
		commandLabel = data.get("commandLabel", "")
		if isinstance(commandLabel, str) and commandLabel.strip():
			normalizedData["commandLabel"] = commandLabel.strip()
	elif itemType == "TextSnippets":
		text = data.get("text", "")
		if not isinstance(text, str):
			text = ""
		action = (data.get("action", TEXT_SNIPPET_ACTION_VALUES[0]) or "").strip().lower()
		if action not in TEXT_SNIPPET_ACTION_VALUES:
			action = TEXT_SNIPPET_ACTION_VALUES[0]
		normalizedData["text"] = text
		normalizedData["action"] = action

	normalizedItem = {
		"name": name,
		"type": itemType,
		"gesture": gesture,
		"data": normalizedData,
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
	return {
		"version": 2,
		"settings": {"verbosity": verbosity},
		"items": items,
	}


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
