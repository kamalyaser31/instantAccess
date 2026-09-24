# -*- coding: utf-8 -*-

import json
import logging
import os
import tempfile
import threading

import addonHandler
import gui
import wx

from .constants import CONFIRM_CAPTION, TEXT_SNIPPET_ACTION_VALUES, TYPE_SECTIONS, VERBOSITY_VALUES
from .timing import parseDelay

addonHandler.initTranslation()
log = logging.getLogger(__name__)
_configLock = threading.RLock()


def _defaultConfig():
	return {
		"version": 3,
		"settings": {"verbosity": VERBOSITY_VALUES[0]},
		"items": [],
	}


def _toNonNegativeFloat(value, defaultValue=0.0):
	try:
		return parseDelay(value)
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
	if itemType == "Keystrokes":
		keys = rawData.get("keys", "")
		if not isinstance(keys, str):
			keys = ""
		pressDelay = _toNonNegativeFloat(rawData.get("pressDelay", 0.05), 0.05)
		return {"keys": keys, "pressDelay": pressDelay}
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
	stopOnError = rawItem.get("stopOnError", True)
	if not isinstance(stopOnError, bool):
		stopOnError = True
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
		"stopOnError": stopOnError,
		"actions": actions,
	}
	if appName:
		normalizedItem["appName"] = appName
	return normalizedItem


def _validateConfig(rawConfig):
	"""Reject malformed data before normalization can silently discard user items."""
	if not isinstance(rawConfig, dict) or not isinstance(rawConfig.get("items"), list):
		raise ValueError("Invalid config format")
	if type(rawConfig.get("version", 3)) is not int or rawConfig.get("version", 3) != 3:
		raise ValueError("Unsupported config version")
	settings = rawConfig.get("settings", {})
	if (
		not isinstance(settings, dict)
		or settings.get("verbosity", VERBOSITY_VALUES[0]) not in VERBOSITY_VALUES
	):
		raise ValueError("Invalid verbosity")
	names = set()
	gestures = set()
	for item in rawConfig["items"]:
		if not isinstance(item, dict):
			raise ValueError("Invalid item")
		for field in ("name", "gesture", "appName"):
			if not isinstance(item.get(field, ""), str):
				raise ValueError(f"Invalid item {field}")
		name = item.get("name", "").strip()
		gesture = item.get("gesture", "").strip().lower()
		appName = item.get("appName", "").strip().lower()
		if not name or not gesture or name in names or (gesture, appName) in gestures:
			raise ValueError("Missing or duplicate item name/gesture")
		names.add(name)
		gestures.add((gesture, appName))
		parseDelay(item.get("interval", 0))
		if not isinstance(item.get("stopOnError", True), bool):
			raise ValueError("Invalid stopOnError")
		actions = item.get("actions")
		if not isinstance(actions, list) or not actions:
			raise ValueError("At least one action is required")
		for action in actions:
			if not isinstance(action, dict) or action.get("type") not in TYPE_SECTIONS:
				raise ValueError("Invalid action type")
			parseDelay(action.get("delay", 0))
			data = action.get("data")
			if not isinstance(data, dict):
				raise ValueError("Invalid action data")
			itemType = action["type"]
			field = {
				"Websites": "url",
				"NvdaCommands": "commandId",
				"TextSnippets": "text",
				"Keystrokes": "keys",
			}.get(itemType, "path")
			if not isinstance(data.get(field), str) or not data[field].strip():
				raise ValueError(f"Invalid action {field}")
			for field in ("arguments", "commandLabel"):
				if field in data and not isinstance(data[field], str):
					raise ValueError(f"Invalid action {field}")
			if itemType == "TextSnippets" and data.get("action", "type") not in TEXT_SNIPPET_ACTION_VALUES:
				raise ValueError("Invalid snippet action")
			for field in ("typingDelay", "pressDelay"):
				if field in data:
					parseDelay(data[field])


def _normalizeConfig(rawConfig):
	_validateConfig(rawConfig)
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
	with _configLock:
		if not os.path.exists(configPath) and not os.path.exists(configPath + ".bak"):
			saveConfig(configPath, _defaultConfig())


def _writeConfigAtomic(configPath, config):
	configDir = os.path.dirname(os.path.abspath(configPath))
	os.makedirs(configDir, exist_ok=True)
	tempPath = None
	try:
		with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=configDir, delete=False) as handle:
			tempPath = handle.name
			json.dump(config, handle, ensure_ascii=False, indent="\t", allow_nan=False)
			handle.flush()
			os.fsync(handle.fileno())
		os.replace(tempPath, configPath)
	finally:
		if tempPath and os.path.exists(tempPath):
			os.unlink(tempPath)


def saveConfig(configPath, config, *, rotateBackup=True):
	"""Only rotate validated data; recovery must leave the last good backup intact."""
	normalized = _normalizeConfig(config)
	with _configLock:
		if rotateBackup and os.path.exists(configPath):
			try:
				previous = loadConfigFromPathStrict(configPath)
			except (ValueError, OSError):
				# An explicit import may replace a damaged primary, but never its backup.
				previous = None
			if previous is not None:
				_writeConfigAtomic(configPath + ".bak", previous)
		_writeConfigAtomic(configPath, normalized)


def _shouldRecoverFromBackup():
	"""Ask the user whether to restore a corrupted config from backup.

	Only shows the dialog when called on the main thread; silently
	recovers when called from a background thread to avoid wx deadlocks (C2).
	"""
	if not wx.IsMainThread():
		return True
	try:
		# Translators: Prompt asking whether to recover corrupted configuration from backup.
		promptMsg = _(
			"The instant Access configuration file appears to be corrupted. "
			"Would you like to restore the previous backup?",
		)
		return gui.messageBox(promptMsg, CONFIRM_CAPTION, wx.YES_NO | wx.ICON_QUESTION) == wx.YES
	except Exception:
		return True


def _tryRecoverFromBackup(backupPath, configPath):
	"""Attempt to restore configuration from a backup file.

	Returns the recovered config dict on success, or None on failure.
	"""
	if not os.path.exists(backupPath):
		return None
	try:
		recovered = loadConfigFromPathStrict(backupPath)
		if not _shouldRecoverFromBackup():
			return None
		saveConfig(configPath, recovered, rotateBackup=False)
		return recovered
	except Exception as e:
		log.error("Failed to restore config from backup %s: %s", backupPath, e)
		return None


def loadConfigSafe(configPath):
	ensureConfigFile(configPath)
	backupPath = configPath + ".bak"
	try:
		with open(configPath, "r", encoding="utf-8") as handle:
			rawConfig = json.load(handle)
		return _normalizeConfig(rawConfig)
	except Exception as e:
		log.error("Failed to load config from %s: %s", configPath, e)
		recovered = _tryRecoverFromBackup(backupPath, configPath)
		if recovered is not None:
			return recovered
		# Keep both files unchanged when recovery is declined or fails.
		return _defaultConfig()


def loadConfigFromPathStrict(configPath):
	with open(configPath, "r", encoding="utf-8") as handle:
		rawConfig = json.load(handle)
	return _normalizeConfig(rawConfig)
