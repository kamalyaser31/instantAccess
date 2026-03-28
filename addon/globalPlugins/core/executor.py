# -*- coding: utf-8 -*-

import addonHandler
import api
import logging
import os
import subprocess
import time
import ui
import webbrowser
import wx

from .nvda_commands import executeNvdaCommand

addonHandler.initTranslation()

try:
	from . import keyboard
except Exception:
	keyboard = None

# Set up logging for better debugging
log = logging.getLogger(__name__)


def expandPath(rawPath):
	"""Expand environment variables and user home directory in a path."""
	if not rawPath:
		return rawPath
	return os.path.expandvars(os.path.expanduser(rawPath))


def queueMessage(message):
	"""Queue a message to be displayed on the main thread."""
	if message:
		wx.CallAfter(ui.message, message)


def _setClipboardText(text):
	"""Set clipboard text using the appropriate NVDA API."""
	try:
		if hasattr(api, "setClipText"):
			api.setClipText(text)
			return True
		if hasattr(api, "copyToClip"):
			return bool(api.copyToClip(text, notify=False))
	except Exception as e:
		log.error("Error setting clipboard text: %s", e)
	return False


def _executeTextSnippet(path, action, typingDelay=0.05):
	"""Execute a text snippet action (type, copy, or paste)."""
	text = path or ""
	action = (action or "type").strip().lower()
	try:
		typingDelay = float(typingDelay)
	except (ValueError, TypeError):
		typingDelay = 0.05
	if typingDelay < 0:
		typingDelay = 0.05
	if not text:
		queueMessage(_("Error: Text snippet is empty"))
		return

	if action == "copy":
		if not _setClipboardText(text):
			queueMessage(_("Error: Could not copy text snippet"))
		return

	if action == "paste":
		if not _setClipboardText(text):
			queueMessage(_("Error: Could not copy text snippet"))
			return
		if keyboard is None:
			queueMessage(_("Error: Keyboard library is not available"))
			return
		try:
			keyboard.send("ctrl+v")
		except Exception as e:
			log.error("Error pasting text snippet: %s", e)
			queueMessage(_("Error: Could not paste text snippet"))
		return

	if keyboard is None:
		queueMessage(_("Error: Keyboard library is not available"))
		return
	try:
		keyboard.write(text, delay=typingDelay)
	except Exception as e:
		log.error("Error typing text snippet: %s", e)
		queueMessage(_("Error: Could not type text snippet"))


def _parseKeystrokeLine(raw_line):
	"""Return (hotkey, repeat_count) from a single non-empty keystroke line.

	Trailing integer suffix sets the repeat count (must be >= 1).
	Unrecognised suffix is treated as part of the hotkey string, not as count.
	Examples:
	  'shift+f10'      -> ('shift+f10', 1)
	  'down 5'         -> ('down', 5)
	  'ctrl+alt+del 3' -> ('ctrl+alt+del', 3)
	  'alt+f4 abc'     -> ('alt+f4 abc', 1)
	"""
	parts = raw_line.rsplit(None, 1)
	if len(parts) == 2:
		try:
			count = int(parts[1])
			if count >= 1:
				return (parts[0].strip(), count)
		except ValueError:
			pass
	return (raw_line, 1)


def _sendKeystrokeSequence(keys_text, press_delay):
	"""Send each line in keys_text as a keyboard hotkey, repeating if a count suffix is given.

	Stops on the first send failure and notifies the user via NVDA speech.
	Caller is responsible for checking keyboard availability and empty input.
	"""
	lines = keys_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
	for raw_line in lines:
		line = raw_line.strip()
		if not line or line.startswith("#"):
			continue
		hotkey, count = _parseKeystrokeLine(line)
		for _ in range(count):
			try:
				keyboard.send(hotkey)
			except Exception as e:
				log.error("Keystroke send failed for '%s': %s", hotkey, e)
				queueMessage(
					_("Error: Could not send keystroke: {key}").format(key=hotkey)
				)
				return
			if press_delay > 0:
				time.sleep(press_delay)


def executeInstantAction(itemType, path, arguments="", textAction="type", typingDelay=0.05, press_delay=0.05):
	"""Execute a single instant action based on its type."""
	if itemType == "Websites":
		url = (path or "").strip()
		if not url:
			queueMessage(_("Error: URL is empty"))
			return
		if not url.lower().startswith(("http://", "https://")):
			url = "https://" + url
		try:
			webbrowser.open(url)
		except Exception as e:
			log.error("Error opening website: %s", e)
			queueMessage(_("Error: Could not open the website"))
		return

	if itemType == "NvdaCommands":
		wx.CallAfter(executeNvdaCommand, (path or "").strip())
		return

	if itemType == "TextSnippets":
		_executeTextSnippet(path, textAction, typingDelay=typingDelay)
		return

	if itemType == "Keystrokes":
		if keyboard is None:
			queueMessage(_("Error: Keyboard library is not available"))
			return
		keys_text = (path or "").strip()
		if not keys_text:
			queueMessage(_("Error: Keystrokes field is empty"))
			return
		_sendKeystrokeSequence(keys_text, press_delay)
		return

	resolvedPath = expandPath(path or "")
	if not resolvedPath or not os.path.exists(resolvedPath):
		queueMessage(_("Error: File not found"))
		return

	if itemType == "Folders":
		try:
			os.startfile(resolvedPath)
		except AttributeError:
			# os.startfile is Windows-only, use xdg-open on Linux or open on macOS
			try:
				if os.name == 'posix':
					import platform
					if platform.system() == 'Darwin':
						subprocess.Popen(['open', resolvedPath])
					else:
						subprocess.Popen(['xdg-open', resolvedPath])
				else:
					queueMessage(_("Error: Could not open the item"))
			except Exception as e:
				log.error("Error opening folder: %s", e)
				queueMessage(_("Error: Could not open the item"))
		except Exception as e:
			log.error("Error opening folder: %s", e)
			queueMessage(_("Error: Could not open the item"))
		return

	if itemType == "Files":
		try:
			if not wx.LaunchDefaultApplication(resolvedPath):
				queueMessage(_("Error: Could not open the file"))
		except Exception as e:
			log.error("Error opening file: %s", e)
			queueMessage(_("Error: Could not open the file"))
		return

	if itemType == "Programs":
		try:
			argumentsText = (arguments or "").strip()
			workingDir = os.path.dirname(resolvedPath) or None
			if argumentsText:
				commandLine = subprocess.list2cmdline([resolvedPath]) + " " + argumentsText
				subprocess.Popen(commandLine, cwd=workingDir)
			else:
				subprocess.Popen([resolvedPath], cwd=workingDir)
		except Exception as e:
			log.error("Error starting program: %s", e)
			queueMessage(_("Error: Could not start the program"))


def executeInstantItem(item):
	"""Execute all actions within an instant item."""
	if not item:
		return
	actions = item.get("actions", [])
	try:
		interval = float(item.get("interval", 0.0) or 0.0)
	except (ValueError, TypeError):
		interval = 0.0
	if interval < 0:
		interval = 0.0
	for index, action in enumerate(actions):
		try:
			delay = float(action.get("delay", 0.0) or 0.0)
		except (ValueError, TypeError):
			delay = 0.0
		if delay > 0:
			time.sleep(delay)
		executeInstantAction(
			itemType=action.get("type", ""),
			path=action.get("path", ""),
			arguments=action.get("arguments", ""),
			textAction=action.get("textAction", "type"),
			typingDelay=action.get("typingDelay", 0.05),
			press_delay=action.get("pressDelay", 0.05),
		)
		if index < len(actions) - 1 and interval > 0:
			time.sleep(interval)
