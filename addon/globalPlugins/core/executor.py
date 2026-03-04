# -*- coding: utf-8 -*-

import api
import os
import subprocess
import ui
import webbrowser
import wx

from .nvda_commands import executeNvdaCommand

try:
	from . import keyboard
except Exception:
	keyboard = None


def expandPath(rawPath):
	if not rawPath:
		return rawPath
	return os.path.expandvars(os.path.expanduser(rawPath))


def queueMessage(message):
	if message:
		wx.CallAfter(ui.message, message)


def _setClipboardText(text):
	if hasattr(api, "setClipText"):
		api.setClipText(text)
		return True
	if hasattr(api, "copyToClip"):
		return bool(api.copyToClip(text, notify=False))
	return False


def _executeTextSnippet(path, action):
	text = path or ""
	action = (action or "type").strip().lower()
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
		except Exception:
			queueMessage(_("Error: Could not paste text snippet"))
		return

	if keyboard is None:
		queueMessage(_("Error: Keyboard library is not available"))
		return
	try:
		keyboard.write(text, delay=0.02)
	except Exception:
		queueMessage(_("Error: Could not type text snippet"))


def executeInstantItem(itemType, path, arguments="", textAction="type"):
	if itemType == "Websites":
		url = (path or "").strip()
		if not url:
			queueMessage(_("Error: URL is empty"))
			return
		if not url.lower().startswith(("http://", "https://")):
			url = "https://" + url
		try:
			webbrowser.open(url)
		except Exception:
			queueMessage(_("Error: Could not open the website"))
		return

	if itemType == "NvdaCommands":
		wx.CallAfter(executeNvdaCommand, (path or "").strip())
		return

	if itemType == "TextSnippets":
		_executeTextSnippet(path, textAction)
		return

	resolvedPath = expandPath(path or "")
	if not resolvedPath or not os.path.exists(resolvedPath):
		queueMessage(_("Error: File not found"))
		return

	if itemType == "Folders":
		try:
			os.startfile(resolvedPath)
		except Exception:
			queueMessage(_("Error: Could not open the item"))
		return

	if itemType == "Files":
		try:
			if not wx.LaunchDefaultApplication(resolvedPath):
				queueMessage(_("Error: Could not open the file"))
		except Exception:
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
		except Exception:
			queueMessage(_("Error: Could not start the program"))
