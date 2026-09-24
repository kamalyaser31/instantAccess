# -*- coding: utf-8 -*-

from dataclasses import dataclass
from locale import strxfrm
from functools import wraps
import logging

import addonHandler
import api
import inputCore
import keyboardHandler
import scriptHandler
import ui
import wx

addonHandler.initTranslation()
log = logging.getLogger(__name__)


COMMAND_ID_SEPARATOR = "|"


@dataclass
class NvdaCommand:
	category: str
	displayName: str
	moduleName: str
	className: str
	scriptName: str

	@property
	def identifier(self):
		return buildCommandIdentifier(self.moduleName, self.className, self.scriptName)

	@property
	def label(self):
		return _("{category}: {command}").format(category=self.category, command=self.displayName)


def buildCommandIdentifier(moduleName, className, scriptName):
	return COMMAND_ID_SEPARATOR.join([moduleName, className, scriptName])


def parseCommandIdentifier(commandId):
	parts = (commandId or "").split(COMMAND_ID_SEPARATOR)
	if len(parts) != 3 or not all(parts):
		return None
	return {"moduleName": parts[0], "className": parts[1], "scriptName": parts[2]}


def _getAllGestureScriptInfo():
	try:
		import gui

		prevFocus = getattr(gui.mainFrame, "prevFocus", None)
		prevFocusAncestors = getattr(gui.mainFrame, "prevFocusAncestors", None)
		if prevFocus:
			mappings = inputCore.manager.getAllGestureMappings(obj=prevFocus, ancestors=prevFocusAncestors)
		else:
			mappings = inputCore.manager.getAllGestureMappings()
	except Exception:
		mappings = inputCore.manager.getAllGestureMappings()
	return mappings


def getAllActiveNvdaCommands():
	mappings = _getAllGestureScriptInfo()
	commands = []
	for category in sorted(mappings.keys(), key=strxfrm):
		scripts = mappings.get(category, {})
		for displayName in sorted(scripts.keys(), key=strxfrm):
			scriptInfo = scripts.get(displayName)
			if not scriptInfo:
				continue
			moduleName = getattr(scriptInfo, "moduleName", "")
			className = getattr(scriptInfo, "className", "")
			scriptName = getattr(scriptInfo, "scriptName", "")
			if not (moduleName and className and scriptName):
				continue
			commands.append(
				NvdaCommand(
					category=category,
					displayName=displayName,
					moduleName=moduleName,
					className=className,
					scriptName=scriptName,
				),
			)
	return commands


def getCommandByIdentifier(commandId):
	for command in getAllActiveNvdaCommands():
		if command.identifier == commandId:
			return command
	return None


class _InstantCommandGesture:
	wasInSayAll = False
	_immediate = True
	identifier = "instantAccess:nvdaCommand"
	identifiers = [identifier]
	displayName = _("instant Access command")

	def __init__(self, script, onComplete=None, isCancelled=None):
		self.script = script
		self.onComplete = onComplete or (lambda success: None)
		self.isCancelled = isCancelled or (lambda: False)

	def send(self):
		return

	def executeScript(self, script):
		_runObservedScript(script, self, self.onComplete, self.isCancelled)


def _runObservedScript(script, gesture, onComplete, isCancelled):
	"""Observe errors before NVDA consumes them, and finish only after script execution."""
	success = False

	@wraps(script)
	def observedScript(inputGesture):
		nonlocal success
		if not isCancelled():
			script(inputGesture)
			success = True

	# Preserve NVDA's repeat-count identity for repeated calls to the same script.
	observedScript.__func__ = getattr(script, "__func__", script)
	try:
		if not isCancelled():
			scriptHandler.executeScript(observedScript, gesture)
	except Exception:
		log.exception("Error executing NVDA command")
	finally:
		if not success and not isCancelled():
			ui.message(_("Error: Could not run NVDA command"))
		onComplete(success and not isCancelled())


def _iterScriptableObjects():
	focus = api.getFocusObject()
	if not focus:
		return
	yield from _safeGetRunningGlobalPlugins()
	app = getattr(focus, "appModule", None)
	if app:
		yield app
	brailleDisplay = _safeGetBrailleDisplay()
	if brailleDisplay:
		yield brailleDisplay
	yield from _safeGetVisionProviders()
	treeInterceptor = getattr(focus, "treeInterceptor", None)
	if treeInterceptor and getattr(treeInterceptor, "isReady", True):
		yield treeInterceptor
	yield focus
	for ancestor in reversed(api.getFocusAncestors()):
		yield ancestor
	yield from _safeGetGlobalCommandObjects()


def _safeGetRunningGlobalPlugins():
	try:
		import globalPluginHandler

		yield from globalPluginHandler.runningPlugins
	except Exception:
		return


def _safeGetBrailleDisplay():
	try:
		import baseObject
		import braille

		display = braille.handler.display if braille.handler and braille.handler.display else None
		if display and isinstance(display, baseObject.ScriptableObject):
			return display
	except Exception:
		return None
	return None


def _safeGetVisionProviders():
	try:
		import baseObject
		import vision

		if not vision.handler:
			return
		for provider in vision.handler.getActiveProviderInstances():
			if isinstance(provider, baseObject.ScriptableObject):
				yield provider
	except Exception:
		return


def _safeGetGlobalCommandObjects():
	try:
		import globalCommands

		yield globalCommands.configProfileActivationCommands
		yield globalCommands.commands
	except Exception:
		return


def _resolveBoundScript(moduleName, className, scriptName):
	targetAttr = f"script_{scriptName}"
	for obj in _iterScriptableObjects() or ():
		for cls in obj.__class__.__mro__:
			if cls.__module__ == moduleName and cls.__name__ == className:
				script = getattr(obj, targetAttr, None)
				if callable(script):
					return script
	return None


def _emulateKeyboardScript(scriptName, onComplete, isCancelled):
	if not scriptName.lower().startswith("kb:"):
		return False
	try:
		gesture = keyboardHandler.KeyboardInputGesture.fromName(scriptName[3:])
		# emulateGesture may queue a script instead of sending to the OS.
		inScript = False

		def executeScript(script):
			nonlocal inScript
			inScript = True
			try:
				_runObservedScript(script, gesture, onComplete, isCancelled)
			finally:
				inScript = False

		gesture.executeScript = executeScript
		originalSend = gesture.send

		def send():
			if isCancelled():
				onComplete(False)
				return
			originalSend()
			if not inScript:
				onComplete(True)

		gesture.send = send
		if isCancelled():
			onComplete(False)
			return False
		inputCore.manager.emulateGesture(gesture)
		return True
	except Exception:
		log.exception("Error emulating NVDA keyboard command")
		onComplete(False)
		return False


def executeNvdaCommand(commandId, onComplete=None, isCancelled=None):
	onComplete = onComplete or (lambda success: None)
	isCancelled = isCancelled or (lambda: False)
	if isCancelled():
		onComplete(False)
		return False
	parsed = parseCommandIdentifier(commandId)
	if not parsed:
		ui.message(_("Error: Invalid NVDA command"))
		onComplete(False)
		return False

	if parsed["scriptName"].lower().startswith("kb:"):
		return _emulateKeyboardScript(parsed["scriptName"], onComplete, isCancelled)

	script = _resolveBoundScript(
		moduleName=parsed["moduleName"],
		className=parsed["className"],
		scriptName=parsed["scriptName"],
	)
	if not script:
		ui.message(_("Error: NVDA command is not currently available"))
		onComplete(False)
		return False

	try:
		gesture = _InstantCommandGesture(script, onComplete, isCancelled)
		scriptHandler.queueScript(script, gesture)
		return True
	except Exception:
		wx.CallAfter(ui.message, _("Error: Could not run NVDA command"))
		onComplete(False)
		return False
