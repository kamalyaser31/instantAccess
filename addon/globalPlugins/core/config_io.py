# -*- coding: utf-8 -*-

import copy
import json
import logging
import os
import shutil

import addonHandler
import gui
import wx

from .constants import CONFIRM_CAPTION, TEXT_SNIPPET_ACTION_VALUES, TYPE_SECTIONS, VERBOSITY_VALUES

addonHandler.initTranslation()
log = logging.getLogger(__name__)


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
	tempPath = configPath + ".tmp"
	backupPath = configPath + ".bak"
	with open(tempPath, "w", encoding="utf-8") as handle:
		json.dump(normalized, handle, ensure_ascii=False, indent="\t")
		handle.flush()
		os.fsync(handle.fileno())
	if os.path.exists(configPath):
		try:
			shutil.copy2(configPath, backupPath)
		except Exception as e:
			log.warning("Could not create config backup: %s", e)
	os.replace(tempPath, configPath)


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
			"Would you like to restore the previous backup?"
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
	if not _shouldRecoverFromBackup():
		return None
	try:
		with open(backupPath, "r", encoding="utf-8") as handle:
			rawConfig = json.load(handle)
		recovered = _normalizeConfig(rawConfig)
		saveConfig(configPath, recovered)
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
		defaultConfig = _defaultConfig()
		saveConfig(configPath, defaultConfig)
		return copy.deepcopy(defaultConfig)


def loadConfigFromPathStrict(configPath):
	with open(configPath, "r", encoding="utf-8") as handle:
		rawConfig = json.load(handle)
	return _normalizeConfig(rawConfig)
