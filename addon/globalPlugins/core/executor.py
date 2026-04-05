# -*- coding: utf-8 -*-

import api
import logging
import os
import subprocess
import time
import ui
import webbrowser
import wx

from .nvda_commands import executeNvdaCommand

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


def executeInstantAction(itemType, path, arguments="", textAction="type", typingDelay=0.05):
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
		)
		if index < len(actions) - 1 and interval > 0:
			time.sleep(interval)
