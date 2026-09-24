# -*- coding: utf-8 -*-

import addonHandler
import api
import logging
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

log = logging.getLogger(__name__)


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
				log.exception("Item execution failed")
				if not self.cancelEvent.is_set():
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
			log.exception("Could not dispatch NVDA command")
			onComplete(False)

	if wx.IsMainThread():
		# Item execution is a worker operation. Refuse to deadlock the main loop.
		log.error("NVDA command execution must be requested from the execution queue")
		return False
	wx.CallAfter(dispatch)
	deadline = time.monotonic() + timeout
	while not completed.wait(0.05):
		if isCancelled() or time.monotonic() >= deadline:
			expired.set()
			if not _isCancelled(cancelEvent):
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


def _executeTextSnippet(path, action, typingDelay=0.05, cancelEvent=None):
	"""Execute a text snippet action (type, copy, or paste). Returns True on success."""
	text = path or ""
	action = (action or "type").strip().lower()
	try:
		typingDelay = parseDelay(typingDelay)
	except (ValueError, TypeError):
		queueMessage(_("Typing delay must be a valid number."))
		return False
	if _isCancelled(cancelEvent):
		return False
	if not text:
		queueMessage(_("Error: Text snippet is empty"))
		return False

	if action == "copy":
		if not _setClipboardText(text):
			queueMessage(_("Error: Could not copy text snippet"))
			return False
		return True

	if action == "paste":
		if not _setClipboardText(text):
			queueMessage(_("Error: Could not copy text snippet"))
			return False
		if keyboard is None:
			queueMessage(_("Error: Keyboard library is not available"))
			return False
		try:
			if _isCancelled(cancelEvent):
				return False
			keyboard.send("ctrl+v")
			return True
		except Exception as e:
			log.error("Error pasting text snippet: %s", e)
			queueMessage(_("Error: Could not paste text snippet"))
			return False

	if keyboard is None:
		queueMessage(_("Error: Keyboard library is not available"))
		return False
	try:
		return keyboard.write(text, delay=typingDelay, cancel_event=cancelEvent) is not False
	except Exception as e:
		log.error("Error typing text snippet: %s", e)
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
				log.error("Keystroke send failed for '%s': %s", hotkey, e)
				queueMessage(
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
			queueMessage(_("Error: URL is empty"))
			return False
		if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", url):
			url = "https://" + url
		try:
			if webbrowser.open(url):
				return True
			queueMessage(_("Error: Could not open the website"))
			return False
		except Exception as e:
			log.error("Error opening website: %s", e)
			queueMessage(_("Error: Could not open the website"))
			return False

	if itemType == "NvdaCommands":
		return _executeNvdaAction((path or "").strip(), cancelEvent)

	if itemType == "TextSnippets":
		return _executeTextSnippet(path, textAction, typingDelay=typingDelay, cancelEvent=cancelEvent)

	if itemType == "Keystrokes":
		if keyboard is None:
			queueMessage(_("Error: Keyboard library is not available"))
			return False
		keys_text = (path or "").strip()
		if not keys_text:
			queueMessage(_("Error: Keystrokes field is empty"))
			return False
		return _sendKeystrokeSequence(keys_text, pressDelay, cancelEvent)

	resolvedPath = expandPath(path or "")
	if not resolvedPath:
		queueMessage(_("Error: File not found"))
		return False

	if itemType == "Folders":
		if not os.path.exists(resolvedPath):
			queueMessage(_("Error: File not found"))
			return False
		try:
			os.startfile(resolvedPath)
			return True
		except Exception as e:
			log.error("Error opening folder: %s", e)
			queueMessage(_("Error: Could not open the item"))
			return False

	if itemType == "Files":
		if not os.path.exists(resolvedPath):
			queueMessage(_("Error: File not found"))
			return False
		try:
			os.startfile(resolvedPath)
			return True
		except Exception:
			try:
				if wx.LaunchDefaultApplication(resolvedPath):
					return True
			except Exception as e:
				log.error("Error opening file: %s", e)
			queueMessage(_("Error: Could not open the file"))
			return False

	if itemType == "Programs":
		if not os.path.exists(resolvedPath):
			whichPath = shutil.which(resolvedPath)
			if whichPath:
				resolvedPath = whichPath
			else:
				queueMessage(_("Error: File not found"))
				return False
		try:
			argumentsText = (arguments or "").strip()
			workingDir = os.path.dirname(resolvedPath) or None
			is_batch = resolvedPath.lower().endswith((".bat", ".cmd"))
			if is_batch:
				# cmd.exe needs its own outer quoting; arguments remain a command-line string.
				interpreter = os.path.join(os.environ["SystemRoot"], "System32", "cmd.exe")
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
			log.error("Error starting program: %s", e)
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
			log.exception("Action %d failed for item '%s'", index, item.get("name"))
			queueMessage(_("Error: Could not run the action"))
			success = False
		allSucceeded = allSucceeded and success
		if not success and stopOnError:
			log.warning("Action %d failed, stopping sequence for item '%s'", index, item.get("name"))
			return False
		if index < len(actions) - 1 and interval > 0:
			if not _wait(interval, cancelEvent):
				return False
	return allSucceeded
