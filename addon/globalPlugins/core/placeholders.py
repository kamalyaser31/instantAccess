# -*- coding: utf-8 -*-
"""Placeholders and context variable resolution for instant Access."""

import addonHandler
from logHandler import log
import os
import re
import shutil
import subprocess
import time
import urllib.parse

addonHandler.initTranslation()

ALLOWED_VARIABLES = {"date", "time", "clipboard", "selection", "file", "folder"}
CONTEXT_VARIABLES = {"selection", "file", "folder"}


def extractVariables(text):
	"""Return set of variable names found in text, ignoring escaped braces."""
	if not text:
		return set()
	cleaned = text.replace("{{", "").replace("}}", "")
	return {
		match.group(1).lower()
		for match in re.finditer(r"\{([a-zA-Z]+)\}", cleaned)
		if match.group(1).lower() in ALLOWED_VARIABLES
	}


def _placeholderText(action):
	"""The one field of an action that can hold placeholders."""
	if action.get("type") in ("Websites", "TextSnippets"):
		return action.get("path", "")
	if action.get("type") == "Programs":
		return action.get("arguments", "")
	return ""


def actionNeedsContext(action):
	return bool(extractVariables(_placeholderText(action)) & CONTEXT_VARIABLES)


def itemNeedsContext(item):
	return any(actionNeedsContext(action) for action in item.get("actions", []))


def _isBatchFile(path):
	"""Resolve the path as the executor does: a bare "npm" can be npm.cmd on the PATH."""
	cleaned = os.path.expandvars(os.path.expanduser((path or "").strip().strip("'\"")))
	resolved = cleaned if os.path.exists(cleaned) else (shutil.which(cleaned) or cleaned)
	return resolved.lower().endswith((".bat", ".cmd"))


def _quotePath(path):
	"""Quote one path; doubling a trailing backslash keeps it from escaping the closing quote."""
	return '"' + re.sub(r"(\\+)$", r"\1\1", path) + '"'


def getSelectionText():
	"""Read selected text from the focus object or tree interceptor on the main thread."""
	try:
		import api
		import textInfos

		obj = api.getFocusObject()
		if not obj:
			return ""
		treeInterceptor = getattr(obj, "treeInterceptor", None)
		if (
			treeInterceptor
			and getattr(treeInterceptor, "isReady", False)
			and not getattr(treeInterceptor, "passThrough", True)
		):
			obj = treeInterceptor
		info = obj.makeTextInfo(textInfos.POSITION_SELECTION)
		return (getattr(info, "text", "") or "").strip()
	except Exception as e:
		log.debugWarning("instantAccess: Could not read selection: %s", e)
		return ""


def getExplorerContext():
	"""Read selected files and current folder from File Explorer on the main thread."""
	try:
		import api

		focus = api.getFocusObject()
		appModule = getattr(focus, "appModule", None)
		appName = (getattr(appModule, "appName", "") or "").strip().lower()
		if appName != "explorer":
			return {"file": "", "folder": "", "fileList": []}
	except Exception:
		return {"file": "", "folder": "", "fileList": []}

	try:
		import comtypes.client
		import winUser

		foregroundHwnd = winUser.getForegroundWindow()
		# Without dynamic dispatch the generated wrapper has no Folder.Self, so the folder reads as empty.
		shell = comtypes.client.CreateObject("Shell.Application", dynamic=True)
		for window in shell.Windows():
			try:
				if getattr(window, "HWND", 0) == foregroundHwnd:
					doc = getattr(window, "Document", None)
					if not doc:
						continue
					folderPath = ""
					try:
						folderPath = str(doc.Folder.Self.Path or "")
					except Exception:
						pass
					selectedPaths = []
					try:
						selectedItems = doc.SelectedItems()
						count = getattr(selectedItems, "Count", 0)
						for i in range(count):
							item = selectedItems.Item(i)
							path = str(getattr(item, "Path", "") or "")
							if path:
								selectedPaths.append(path)
					except Exception:
						pass
					if selectedPaths:
						if len(selectedPaths) > 1:
							fileStr = subprocess.list2cmdline(selectedPaths)
						else:
							fileStr = selectedPaths[0]
					else:
						fileStr = ""
					return {
						"file": fileStr,
						"folder": folderPath,
						"fileList": selectedPaths,
					}
			except Exception:
				continue
	except Exception as e:
		log.debugWarning("instantAccess: Error querying File Explorer via COM: %s", e)

	return {"file": "", "folder": "", "fileList": []}


def captureContextSnapshot():
	"""Capture main-thread context (selection, file, folder) before dispatching to worker."""
	exp = getExplorerContext()
	return {
		"selection": getSelectionText(),
		"file": exp.get("file", ""),
		"folder": exp.get("folder", ""),
		"fileList": exp.get("fileList", []),
	}


def validateItemContext(item, context=None):
	"""Check for safety and missing context variables before running any action in an item.

	Returns (True, None) if valid, or (False, error_message) if execution should stop.
	"""
	context = context or {}
	for action in item.get("actions", []):
		variables = extractVariables(_placeholderText(action))
		# cmd.exe would run & or | in the replaced text as commands.
		if (
			action.get("type") == "Programs"
			and variables & (CONTEXT_VARIABLES | {"clipboard"})
			and _isBatchFile(action.get("path", ""))
		):
			# Translators: Announced when variables are used in arguments of a batch file.
			return False, _("Error: Cannot use variables in batch file arguments.")
		if "selection" in variables and not context.get("selection"):
			# Translators: Announced when {selection} is used but nothing is selected.
			return False, _("No text is selected.")
		if "file" in variables and not context.get("file"):
			# Translators: Announced when {file} is used but no file is selected in File Explorer.
			return False, _("No file is selected in File Explorer.")
		if "folder" in variables and not context.get("folder"):
			# Translators: Announced when {folder} is used but no folder is open in File Explorer.
			return False, _("No folder is open in File Explorer.")
	return True, None


def resolveVariable(varName, context=None, getClipboardFn=None, encoding="raw"):
	"""Resolve a single variable value according to its encoding mode."""
	varName = varName.lower()
	if context is None:
		context = {}
	if varName == "date":
		val = time.strftime("%x")
	elif varName == "time":
		val = time.strftime("%X")
	elif varName == "clipboard":
		val = getClipboardFn() if getClipboardFn else ""
	elif varName == "selection":
		val = context.get("selection", "")
	elif varName == "file":
		val = context.get("file", "")
	elif varName == "folder":
		val = context.get("folder", "")
	else:
		return None

	val = str(val or "")
	if encoding == "url":
		return urllib.parse.quote(val)
	if encoding == "argument":
		if varName in ("file", "folder"):
			paths = (varName == "file" and context.get("fileList")) or [val]
			return " ".join(_quotePath(path) for path in paths)
		return subprocess.list2cmdline([val])
	return val


def substitutePlaceholders(text, context=None, getClipboardFn=None, encoding="raw"):
	"""Replace {date}, {time}, {clipboard}, {selection}, {file}, {folder}.

	Escaped braces {{ and }} are unescaped to { and }.
	"""
	if not text:
		return text

	escaped = text.replace("{{", "\x00").replace("}}", "\x01")

	def repl(match):
		varName = match.group(1).lower()
		resolved = resolveVariable(
			varName, context=context, getClipboardFn=getClipboardFn, encoding=encoding
		)
		if resolved is not None:
			return resolved
		return match.group(0)

	result = re.sub(r"\{([a-zA-Z]+)\}", repl, escaped)
	return result.replace("\x00", "{").replace("\x01", "}")
