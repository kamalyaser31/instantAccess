# -*- coding: utf-8 -*-

import json
from logHandler import log
import os
import tempfile
import threading

import addonHandler
import gui
import NVDAState
import wx

from .constants import (
	ACTION_FIELDS,
	BROWSE_FORMAT_VALUES,
	BROWSE_ORDER_VALUES,
	CONFIRM_CAPTION,
	ANNOUNCE_VALUES,
	DEFAULT_SETTINGS,
	TEXT_SNIPPET_ACTION_VALUES,
	TYPE_SECTIONS,
	VERBOSITY_VALUES,
)
from .gestures import appNamesConflict, gestureKey, parseAppNames
from .timing import parseDelay

addonHandler.initTranslation()
_configLock = threading.RLock()


def _defaultConfig():
	return {
		"version": 3,
		"settings": dict(DEFAULT_SETTINGS),
		"items": [],
	}


# The _normalize* helpers run only after _validateConfig, so they transform values and never repair them.
def _normalizeActionData(itemType, rawData):
	data = {ACTION_FIELDS[itemType]: rawData[ACTION_FIELDS[itemType]]}
	if itemType == "Programs" and rawData.get("arguments", "").strip():
		data["arguments"] = rawData["arguments"].strip()
	elif itemType == "NvdaCommands" and rawData.get("commandLabel", "").strip():
		data["commandLabel"] = rawData["commandLabel"].strip()
	elif itemType == "TextSnippets":
		data["action"] = rawData.get("action", TEXT_SNIPPET_ACTION_VALUES[0])
		data["typingDelay"] = parseDelay(rawData.get("typingDelay", 0.05))
	elif itemType == "Keystrokes":
		data["pressDelay"] = parseDelay(rawData.get("pressDelay", 0.05))
	if itemType == "Programs" and rawData.get("runAsAdmin"):
		data["runAsAdmin"] = True
	return data


def _normalizeAction(rawAction):
	itemType = rawAction["type"]
	return {
		"type": itemType,
		"data": _normalizeActionData(itemType, rawAction["data"]),
		"delay": parseDelay(rawAction.get("delay", 0.0)),
	}


def _normalizeItem(rawItem):
	normalizedItem = {
		"name": rawItem["name"].strip(),
		"gesture": rawItem["gesture"].strip().lower(),
		"interval": parseDelay(rawItem.get("interval", 0.0)),
		"stopOnError": rawItem.get("stopOnError", True),
		"actions": [_normalizeAction(rawAction) for rawAction in rawItem["actions"]],
	}
	appName = ", ".join(parseAppNames(rawItem.get("appName", "")))
	if appName:
		normalizedItem["appName"] = appName
	if rawItem.get("enabled", True) is False:
		normalizedItem["enabled"] = False
	if rawItem.get("announceName", ANNOUNCE_VALUES[0]) != ANNOUNCE_VALUES[0]:
		normalizedItem["announceName"] = rawItem["announceName"]
	return normalizedItem


def _validateConfig(rawConfig):
	"""Reject malformed data before normalization can silently discard user items."""
	if not isinstance(rawConfig, dict) or not isinstance(rawConfig.get("items"), list):
		raise ValueError("Invalid config format")
	if type(rawConfig.get("version", 3)) is not int or rawConfig.get("version", 3) != 3:
		raise ValueError("Unsupported config version")
	_validateSettings(rawConfig.get("settings", {}))
	names = set()
	gestures = {}
	for item in rawConfig["items"]:
		if not isinstance(item, dict):
			raise ValueError("Invalid item")
		for field in ("name", "gesture", "appName"):
			if not isinstance(item.get(field, ""), str):
				raise ValueError(f"Invalid item {field}")
		name = item.get("name", "").strip()
		gesture = item.get("gesture", "").strip().lower()
		appName = item.get("appName", "")
		sameGesture = gestures.setdefault(gestureKey(gesture), [])
		if (
			not name
			or not gesture
			or name in names
			or any(appNamesConflict(appName, other) for other in sameGesture)
		):
			raise ValueError("Missing or duplicate item name/gesture")
		names.add(name)
		sameGesture.append(appName)
		parseDelay(item.get("interval", 0))
		if not isinstance(item.get("stopOnError", True), bool):
			raise ValueError("Invalid stopOnError")
		if not isinstance(item.get("enabled", True), bool):
			raise ValueError("Invalid enabled")
		if item.get("announceName", ANNOUNCE_VALUES[0]) not in ANNOUNCE_VALUES:
			raise ValueError("Invalid announceName")
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
			requiredField = ACTION_FIELDS[itemType]
			if not isinstance(data.get(requiredField), str) or not data[requiredField].strip():
				raise ValueError(f"Invalid action {requiredField}")
			for optionalField in ("arguments", "commandLabel"):
				if optionalField in data and not isinstance(data[optionalField], str):
					raise ValueError(f"Invalid action {optionalField}")
			if not isinstance(data.get("runAsAdmin", False), bool):
				raise ValueError("Invalid action runAsAdmin")
			if itemType == "TextSnippets" and data.get("action", "type") not in TEXT_SNIPPET_ACTION_VALUES:
				raise ValueError("Invalid snippet action")
			for timingField in ("typingDelay", "pressDelay"):
				if timingField in data:
					parseDelay(data[timingField])


_SETTING_CHOICES = {
	"verbosity": VERBOSITY_VALUES,
	"browseFormat": BROWSE_FORMAT_VALUES,
	"browseOrder": BROWSE_ORDER_VALUES,
}


def _validateSettings(settings):
	if not isinstance(settings, dict):
		raise ValueError("Invalid settings")
	for key, choices in _SETTING_CHOICES.items():
		if settings.get(key, DEFAULT_SETTINGS[key]) not in choices:
			raise ValueError(f"Invalid {key}")
	for key in ("browseEnabled", "announceName"):
		if not isinstance(settings.get(key, False), bool):
			raise ValueError(f"Invalid {key}")


def _normalizeSettings(settings):
	return {key: settings.get(key, defaultValue) for key, defaultValue in DEFAULT_SETTINGS.items()}


def _normalizeConfig(rawConfig):
	_validateConfig(rawConfig)
	return {
		"version": 3,
		"settings": _normalizeSettings(rawConfig.get("settings", {})),
		"items": [_normalizeItem(rawItem) for rawItem in rawConfig["items"]],
	}


class DiskWriteDisabledError(OSError):
	"""NVDA runs from the launcher or in secure mode, where add-ons must not write settings."""


def ensureConfigFile(configPath):
	if not NVDAState.shouldWriteToDisk():
		return
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
	if not NVDAState.shouldWriteToDisk():
		raise DiskWriteDisabledError("NVDA does not allow writing settings now")
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
		if NVDAState.shouldWriteToDisk():
			saveConfig(configPath, recovered, rotateBackup=False)
		return recovered
	except Exception as e:
		log.error("instantAccess: Failed to restore config from backup %s: %s", backupPath, e)
		return None


def loadConfigSafe(configPath):
	ensureConfigFile(configPath)
	backupPath = configPath + ".bak"
	if not os.path.exists(configPath) and not os.path.exists(backupPath):
		# Expected from the launcher, where ensureConfigFile must not create the file.
		log.debugWarning("instantAccess: no config file yet; using defaults")
		return _defaultConfig()
	try:
		with open(configPath, "r", encoding="utf-8") as handle:
			rawConfig = json.load(handle)
		return _normalizeConfig(rawConfig)
	except Exception as e:
		log.error("instantAccess: Failed to load config from %s: %s", configPath, e)
		recovered = _tryRecoverFromBackup(backupPath, configPath)
		if recovered is not None:
			return recovered
		# Keep both files unchanged when recovery is declined or fails.
		return _defaultConfig()


def loadConfigFromPathStrict(configPath):
	with open(configPath, "r", encoding="utf-8") as handle:
		rawConfig = json.load(handle)
	return _normalizeConfig(rawConfig)
