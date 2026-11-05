# -*- coding: utf-8 -*-

from logHandler import log

import inputCore
import keyboardHandler
import re
import wx

from .constants import CATEGORY_LABEL



# Captured key names that the keyboard library spells differently.
_KEYSTROKE_NAMES = {
	"leftarrow": "left",
	"rightarrow": "right",
	"uparrow": "up",
	"downarrow": "down",
	"pageup": "page up",
	"pagedown": "page down",
	",": "comma",
}


def parseAppNames(value):
	"""The app names in a stored or typed list, lower case, without repeats, in their order.

	The Arabic comma counts too, because an Arabic keyboard layout types it.
	"""
	names = (name.strip().lower() for name in re.split("[,\u060c]", value or ""))
	return list(dict.fromkeys(name for name in names if name))


def appNamesConflict(first, second):
	"""Two items with one shortcut clash when both are global or when they share an app."""
	firstNames, secondNames = set(parseAppNames(first)), set(parseAppNames(second))
	return bool(firstNames & secondNames) or not (firstNames or secondNames)


def gestureToKeystroke(gestureName):
	"""Turn a captured shortcut into the text the Keystrokes action sends."""
	parts = [part for part in gestureName.split("+") if part]
	if gestureName.endswith("+"):
		parts.append("plus")
	return "+".join(_KEYSTROKE_NAMES.get(part.lower(), part.lower()) for part in parts)


def formatGestureForDisplay(gesture):
	if not gesture:
		return ""
	gesture = gesture.strip()
	if gesture.lower().startswith("kb:"):
		return gesture[3:]
	return gesture


def gestureDisplayText(gesture):
	"""The shortcut as NVDA's Input Gestures dialog shows it (localized key names).

	Built from the identifier alone. KeyboardInputGesture.fromName would ask the active keyboard
	layout for letters, which gives a wrong label under layouts without Latin letters, such as Arabic.
	"""
	name = formatGestureForDisplay(gesture)
	if not name:
		return ""
	try:
		label = inputCore.getDisplayTextForGestureIdentifier(gestureKey(gesture))[1]
	except Exception:
		label = None
	return label if isinstance(label, str) and label else name


def normalizeGesture(gesture):
	if not gesture:
		return ""
	gesture = gesture.strip()
	if gesture.lower().startswith("kb:"):
		gesture = gesture[3:]
	gesture = gesture.strip()
	if not gesture:
		return ""
	return "kb:" + gesture.lower()


def gestureKey(gesture):
	"""Match NVDA's own lookup: lower case with sorted modifiers, so modifier order never matters.

	NVDA sends a layout-free kb: identifier with every key press, so one key covers all layouts.
	"""
	gesture = (gesture or "").strip()
	if not gesture:
		return ""
	return inputCore.normalizeGestureIdentifier(gesture)


def getAddonGestures(scriptDescription, fallback):
	"""Gestures bound to one of this add-on's scripts, read at call time so Input Gestures changes apply."""
	try:
		categoryMap = inputCore.manager.getAllGestureMappings().get(CATEGORY_LABEL, {})
		scriptInfo = categoryMap.get(scriptDescription)
		if scriptInfo and getattr(scriptInfo, "gestures", None):
			return list(scriptInfo.gestures)
	except Exception as e:
		log.warning("instantAccess: Error retrieving gestures for '%s': %s", scriptDescription, e)
	return list(fallback)


def validateGestureName(gestureName):
	if not gestureName:
		return False
	try:
		keyboardHandler.KeyboardInputGesture.fromName(gestureName)
		return True
	except Exception:
		return False


def getKeyNameFromEvent(event):
	keyCode = event.GetKeyCode()
	if keyCode in (wx.WXK_SHIFT, wx.WXK_CONTROL, wx.WXK_ALT, wx.WXK_WINDOWS_LEFT, wx.WXK_WINDOWS_RIGHT):
		return ""
	if wx.WXK_F1 <= keyCode <= wx.WXK_F24:
		return f"f{keyCode - wx.WXK_F1 + 1}"
	if wx.WXK_NUMPAD0 <= keyCode <= wx.WXK_NUMPAD9:
		return f"numpad{keyCode - wx.WXK_NUMPAD0}"
	keyMap = {
		wx.WXK_RETURN: "enter",
		wx.WXK_ESCAPE: "escape",
		wx.WXK_SPACE: "space",
		wx.WXK_TAB: "tab",
		wx.WXK_BACK: "backspace",
		wx.WXK_DELETE: "delete",
		wx.WXK_INSERT: "insert",
		wx.WXK_HOME: "home",
		wx.WXK_END: "end",
		wx.WXK_PAGEUP: "pageup",
		wx.WXK_PAGEDOWN: "pagedown",
		wx.WXK_LEFT: "leftArrow",
		wx.WXK_RIGHT: "rightArrow",
		wx.WXK_UP: "upArrow",
		wx.WXK_DOWN: "downArrow",
		wx.WXK_ADD: "numpadPlus",
		wx.WXK_SUBTRACT: "numpadMinus",
		wx.WXK_MULTIPLY: "numpadMultiply",
		wx.WXK_DIVIDE: "numpadDivide",
		wx.WXK_NUMPAD_DECIMAL: "numpadDecimal",
		wx.WXK_NUMPAD_ENTER: "numpadEnter",
	}
	if keyCode in keyMap:
		return keyMap[keyCode]
	unicodeKey = event.GetUnicodeKey()
	if unicodeKey != wx.WXK_NONE and unicodeKey >= 32:
		char = chr(unicodeKey)
		return char.lower()
	if 32 <= keyCode <= 126:
		return chr(keyCode).lower()
	return ""


def buildGestureNameFromEvent(event):
	keyName = getKeyNameFromEvent(event)
	if not keyName:
		return ""
	modifiers = []
	if event.ControlDown():
		modifiers.append("control")
	if event.AltDown():
		modifiers.append("alt")
	if event.ShiftDown():
		modifiers.append("shift")
	if event.MetaDown():
		modifiers.append("windows")
	return "+".join(modifiers + [keyName])
