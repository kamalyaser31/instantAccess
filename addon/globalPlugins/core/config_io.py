# -*- coding: utf-8 -*-

import configparser
import os

from .constants import CONFIG_SECTIONS


def ensureConfigParser():
	config = configparser.ConfigParser(delimiters=("="))
	config.optionxform = str
	return config


def ensureConfigFile(configPath):
	configDir = os.path.dirname(configPath)
	os.makedirs(configDir, exist_ok=True)
	if not os.path.exists(configPath):
		config = ensureConfigParser()
		for section in CONFIG_SECTIONS:
			config.add_section(section)
		with open(configPath, "w", encoding="utf-8") as handle:
			config.write(handle)


def saveConfig(configPath, config):
	configDir = os.path.dirname(configPath)
	os.makedirs(configDir, exist_ok=True)
	with open(configPath, "w", encoding="utf-8") as handle:
		config.write(handle)


def loadConfigSafe(configPath):
	ensureConfigFile(configPath)
	config = ensureConfigParser()
	try:
		with open(configPath, "r", encoding="utf-8") as handle:
			config.read_file(handle)
	except (OSError, configparser.Error):
		config = ensureConfigParser()
		for section in CONFIG_SECTIONS:
			config.add_section(section)
		saveConfig(configPath, config)
	return config
