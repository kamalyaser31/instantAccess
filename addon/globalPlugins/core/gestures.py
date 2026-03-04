# -*- coding: utf-8 -*-

import keyboardHandler
import wx


def formatGestureForDisplay(gesture):
	if not gesture:
		return ""
	gesture = gesture.strip()
	if gesture.lower().startswith("kb:"):
		return gesture[3:]
	return gesture


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


def normalizeGestureIdentifier(gestureId):
	if not gestureId:
		return ""
	gestureId = gestureId.strip().lower()
	if gestureId.startswith("kb("):
		closeIndex = gestureId.find("):")
		if closeIndex != -1:
			return "kb:" + gestureId[closeIndex + 2 :]
	return gestureId


def expandGestureLayouts(gesture):
	gesture = (gesture or "").strip()
	if not gesture:
		return []
	if gesture.lower().startswith("kb:"):
		return [gesture, "kb(laptop):" + gesture[3:]]
	return [gesture]


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
