# -*- coding: utf-8 -*-

from dataclasses import dataclass
from locale import strxfrm

import addonHandler
import api
import inputCore
import keyboardHandler
import scriptHandler
import ui
import wx

addonHandler.initTranslation()
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
	if len(parts) != 3:
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

	def __init__(self, script):
		self.script = script

	def send(self):
		return

	def executeScript(self, script):
		return scriptHandler.executeScript(script, self)


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


def _emulateKeyboardScript(scriptName):
	if not scriptName.lower().startswith("kb:"):
		return False
	try:
		gesture = keyboardHandler.KeyboardInputGesture.fromName(scriptName[3:])
		inputCore.manager.emulateGesture(gesture)
		return True
	except Exception:
		return False


def executeNvdaCommand(commandId):
	parsed = parseCommandIdentifier(commandId)
	if not parsed:
		ui.message(_("Error: Invalid NVDA command"))
		return False

	if _emulateKeyboardScript(parsed["scriptName"]):
		return True

	script = _resolveBoundScript(
		moduleName=parsed["moduleName"],
		className=parsed["className"],
		scriptName=parsed["scriptName"],
	)
	if not script:
		ui.message(_("Error: NVDA command is not currently available"))
		return False

	try:
		gesture = _InstantCommandGesture(script)
		scriptHandler.queueScript(script, gesture)
		return True
	except Exception:
		wx.CallAfter(ui.message, _("Error: Could not run NVDA command"))
		return False
