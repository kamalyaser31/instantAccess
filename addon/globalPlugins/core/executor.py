# -*- coding: utf-8 -*-

import addonHandler
import api
from logHandler import log
import os
import re
import shutil
import subprocess
import time
import copy
import threading
from concurrent.futures import ThreadPoolExecutor
import ui
import webbrowser
import wx

from .nvda_commands import executeNvdaCommand
from .timing import parseDelay

addonHandler.initTranslation()

try:
	from . import keyboard
except Exception:
	keyboard = None



def _isCancelled(cancelEvent):
	return cancelEvent is not None and cancelEvent.is_set()


def _wait(delay, cancelEvent=None):
	delay = parseDelay(delay)
	if cancelEvent is not None:
		return not cancelEvent.wait(delay)
	if delay:
		time.sleep(delay)
	return True


class ExecutionQueue:
	"""Serialize complete items and action tests, with bounded, cancellable work."""

	def __init__(self):
		self.cancelEvent = threading.Event()
		self._slots = threading.BoundedSemaphore(32)
		self._lock = threading.Lock()
		self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="instantAccess")

	def submit(self, item, preDelay=0):
		with self._lock:
			if self.cancelEvent.is_set():
				return None
			if not self._slots.acquire(blocking=False):
				# Translators: Announced when too many items are queued to run.
				queueMessage(_("Too many items are waiting. Please try again later."))
				return None
			try:
				future = self._executor.submit(self._run, copy.deepcopy(item), parseDelay(preDelay))
			except Exception:
				self._slots.release()
				raise
			future.add_done_callback(self._onDone)
			return future

	def _onDone(self, future):
		self._slots.release()
		if not future.cancelled():
			try:
				future.result()
			except Exception:
				log.exception("instantAccess: Item execution failed")
				if not self.cancelEvent.is_set():
					# Translators: Announced when an item stopped because of an unexpected error.
					queueMessage(_("Error: Could not run the item"))

	def _run(self, item, preDelay):
		if not _wait(preDelay, self.cancelEvent):
			return False
		if item.get("name"):
			queueMessage(item["name"])
		return executeInstantItem(item, self.cancelEvent)

	def shutdown(self):
		with self._lock:
			self.cancelEvent.set()
			self._executor.shutdown(wait=False, cancel_futures=True)


def _executeNvdaAction(commandId, cancelEvent=None, timeout=30):
	"""Wait in the worker until the actual queued script finishes, never in the UI."""
	completed = threading.Event()
	expired = threading.Event()
	result = [False]

	def isCancelled():
		return expired.is_set() or _isCancelled(cancelEvent)

	def onComplete(success):
		result[0] = bool(success)
		completed.set()

	def dispatch():
		if isCancelled():
			onComplete(False)
			return
		try:
			executeNvdaCommand(commandId, onComplete=onComplete, isCancelled=isCancelled)
		except Exception:
			log.exception("instantAccess: Could not dispatch NVDA command")
			onComplete(False)

	if wx.IsMainThread():
		# Item execution is a worker operation. Refuse to deadlock the main loop.
		log.error("instantAccess: NVDA command execution must be requested from the execution queue")
		return False
	wx.CallAfter(dispatch)
	deadline = time.monotonic() + timeout
	while not completed.wait(0.05):
		if isCancelled() or time.monotonic() >= deadline:
			expired.set()
			if not _isCancelled(cancelEvent):
				# Translators: Announced when an NVDA command action takes too long.
				queueMessage(_("Error: NVDA command did not finish in time"))
			# A timed-out command must not race subsequent actions, even in continue mode.
			raise TimeoutError("NVDA command did not finish in time")
	return result[0] and not isCancelled()


def expandPath(rawPath):
	"""Expand environment variables and user home directory in a path."""
	if not rawPath:
		return rawPath
	cleaned = rawPath.strip().strip("'\"")
	return os.path.expandvars(os.path.expanduser(cleaned))


def queueMessage(message):
	"""Queue a message to be displayed on the main thread."""
	if message:
		wx.CallAfter(ui.message, message)


def setClipboardText(text):
	"""Copy text to the clipboard with NVDA's API. Returns True on success."""
	try:
		return bool(api.copyToClip(text, notify=False))
	except Exception as e:
		log.error("instantAccess: Error setting clipboard text: %s", e)
		return False


def _executeTextSnippet(path, action, typingDelay=0.05, cancelEvent=None):
	"""Execute a text snippet action (type, copy, or paste). Returns True on success."""
	text = path or ""
	action = (action or "type").strip().lower()
	try:
		typingDelay = parseDelay(typingDelay)
	except (ValueError, TypeError):
		# Translators: Announced when a stored typing delay is invalid.
		queueMessage(_("Typing delay must be a valid number."))
		return False
	if _isCancelled(cancelEvent):
		return False
	if not text:
		# Translators: Announced when a text snippet action has no text.
		queueMessage(_("Error: Text snippet is empty"))
		return False

	if action == "copy":
		if not setClipboardText(text):
			# Translators: Announced when the snippet text could not be copied to the clipboard.
			queueMessage(_("Error: Could not copy text snippet"))
			return False
		return True

	if action == "paste":
		if not setClipboardText(text):
			# Translators: Announced when the snippet text could not be copied before pasting.
			queueMessage(_("Error: Could not copy text snippet"))
			return False
		if keyboard is None:
			# Translators: Announced when simulated key presses are unavailable.
			queueMessage(_("Error: Keyboard library is not available"))
			return False
		try:
			if _isCancelled(cancelEvent):
				return False
			keyboard.send("ctrl+v")
			return True
		except Exception as e:
			log.error("instantAccess: Error pasting text snippet: %s", e)
			# Translators: Announced when pasting a snippet failed.
			queueMessage(_("Error: Could not paste text snippet"))
			return False

	if keyboard is None:
		# Translators: Announced when simulated typing is unavailable.
		queueMessage(_("Error: Keyboard library is not available"))
		return False
	try:
		return keyboard.write(text, delay=typingDelay, cancel_event=cancelEvent) is not False
	except Exception as e:
		log.error("instantAccess: Error typing text snippet: %s", e)
		# Translators: Announced when typing a snippet failed.
		queueMessage(_("Error: Could not type text snippet"))
		return False


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


def _sendKeystrokeSequence(keys_text, pressDelay, cancelEvent=None):
	"""Send each line in keys_text as a keyboard hotkey, repeating if a count suffix is given.

	Stops on the first send failure and notifies the user via NVDA speech.
	Caller is responsible for checking keyboard availability and empty input.
	Returns True on success, False on failure.
	"""
	pressDelay = parseDelay(pressDelay)
	lines = keys_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
	for raw_line in lines:
		line = raw_line.strip()
		if not line or line.startswith("#"):
			continue
		hotkey, count = _parseKeystrokeLine(line)
		for repeatIndex in range(count):
			if _isCancelled(cancelEvent):
				return False
			try:
				keyboard.send(hotkey)
			except Exception as e:
				log.error("instantAccess: Keystroke send failed for '%s': %s", hotkey, e)
				queueMessage(
					# Translators: Announced when a key press failed. {key} is the key name, for example ctrl+c.
					_("Error: Could not send keystroke: {key}").format(key=hotkey),
				)
				return False
			if not _wait(pressDelay, cancelEvent):
				return False
	return True


def executeInstantAction(action, cancelEvent=None):
	"""Execute a single instant action based on its type. Returns True on success, False on failure.

	*action* is a dict with keys: type, path, arguments, textAction, typingDelay, pressDelay.
	"""
	if _isCancelled(cancelEvent):
		return False
	itemType = action.get("type", "")
	path = action.get("path", "")
	arguments = action.get("arguments", "")
	textAction = action.get("textAction", "type")
	typingDelay = action.get("typingDelay", 0.05)
	pressDelay = action.get("pressDelay", 0.05)

	if itemType == "Websites":
		url = (path or "").strip().strip("'\"")
		if not url:
			# Translators: Announced when a website action has no address.
			queueMessage(_("Error: URL is empty"))
			return False
		if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", url):
			url = "https://" + url
		try:
			if webbrowser.open(url):
				return True
			# Translators: Announced when the browser could not open the address.
			queueMessage(_("Error: Could not open the website"))
			return False
		except Exception as e:
			log.error("instantAccess: Error opening website: %s", e)
			# Translators: Announced when opening the address raised an error.
			queueMessage(_("Error: Could not open the website"))
			return False

	if itemType == "NvdaCommands":
		return _executeNvdaAction((path or "").strip(), cancelEvent)

	if itemType == "TextSnippets":
		return _executeTextSnippet(path, textAction, typingDelay=typingDelay, cancelEvent=cancelEvent)

	if itemType == "Keystrokes":
		if keyboard is None:
			# Translators: Announced when simulated keystrokes are unavailable.
			queueMessage(_("Error: Keyboard library is not available"))
			return False
		keys_text = (path or "").strip()
		if not keys_text:
			# Translators: Announced when a keystrokes action has no keys.
			queueMessage(_("Error: Keystrokes field is empty"))
			return False
		return _sendKeystrokeSequence(keys_text, pressDelay, cancelEvent)

	resolvedPath = expandPath(path or "")
	if not resolvedPath:
		# Translators: Announced when the path of an action is empty.
		queueMessage(_("Error: File not found"))
		return False

	if itemType in ("Folders", "Files"):
		if not os.path.exists(resolvedPath):
			# Translators: Announced when the folder or file of an action does not exist.
			queueMessage(_("Error: File not found"))
			return False
		try:
			os.startfile(resolvedPath)
			return True
		except Exception as e:
			log.error("instantAccess: Error opening %s: %s", itemType, e)
			if itemType == "Folders":
				# Translators: Announced when a folder could not be opened.
				queueMessage(_("Error: Could not open the item"))
			else:
				# Translators: Announced when a file could not be opened.
				queueMessage(_("Error: Could not open the file"))
			return False

	if itemType == "Programs":
		if not os.path.exists(resolvedPath):
			whichPath = shutil.which(resolvedPath)
			if whichPath:
				resolvedPath = whichPath
			else:
				# Translators: Announced when a program does not exist and is not on the PATH.
				queueMessage(_("Error: File not found"))
				return False
		try:
			argumentsText = (arguments or "").strip()
			workingDir = os.path.dirname(resolvedPath) or None
			is_batch = resolvedPath.lower().endswith((".bat", ".cmd"))
			if is_batch:
				# cmd.exe needs its own outer quoting; arguments remain a command-line string.
				systemRoot = os.environ.get("SystemRoot", os.environ.get("windir", r"C:\Windows"))
				interpreter = os.path.join(systemRoot, "System32", "cmd.exe")
				batchCommand = f'"{os.path.abspath(resolvedPath)}"'
				if argumentsText:
					batchCommand += " " + argumentsText
				commandLine = subprocess.list2cmdline([interpreter]) + f' /d /s /c "{batchCommand}"'
				subprocess.Popen(commandLine, cwd=workingDir)
			elif argumentsText:
				commandLine = subprocess.list2cmdline([resolvedPath]) + " " + argumentsText
				subprocess.Popen(commandLine, cwd=workingDir)
			else:
				subprocess.Popen([resolvedPath], cwd=workingDir)
			return True
		except Exception as e:
			log.error("instantAccess: Error starting program: %s", e)
			# Translators: Announced when a program failed to start.
			queueMessage(_("Error: Could not start the program"))
			return False

	return False


def executeInstantItem(item, cancelEvent=None):
	"""Execute all actions within an instant item."""
	if not item:
		return False
	actions = item.get("actions", [])
	stopOnError = bool(item.get("stopOnError", True))
	try:
		interval = parseDelay(item.get("interval", 0.0))
	except (ValueError, TypeError):
		# Translators: Announced when the stored interval between actions is invalid.
		queueMessage(_("Interval must be a valid number."))
		return False
	allSucceeded = True
	for index, action in enumerate(actions):
		if _isCancelled(cancelEvent):
			return False
		try:
			if not _wait(action.get("delay", 0.0), cancelEvent):
				return False
			success = executeInstantAction(action, cancelEvent)
		except TimeoutError:
			return False
		except Exception:
			log.exception("instantAccess: Action %d failed for item '%s'", index, item.get("name"))
			# Translators: Announced when an action raised an unexpected error.
			queueMessage(_("Error: Could not run the action"))
			success = False
		allSucceeded = allSucceeded and success
		if not success and stopOnError:
			log.warning(
				"instantAccess: Action %d failed, stopping sequence for item '%s'",
				index,
				item.get("name"),
			)
			return False
		if index < len(actions) - 1 and interval > 0:
			if not _wait(interval, cancelEvent):
				return False
	return allSucceeded
