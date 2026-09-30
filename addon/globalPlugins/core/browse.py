# -*- coding: utf-8 -*-
"""Pure helpers for browsing items inside the instant Access layer."""

import addonHandler
import keyboardHandler

from .gestures import formatGestureForDisplay

addonHandler.initTranslation()


def resolveItem(candidates, currentAppName):
	"""Pick the item a gesture runs in the current app: app-specific first, then global."""
	for candidate in candidates:
		if candidate.get("appName", "") and candidate["appName"] == currentAppName:
			return candidate
	for candidate in candidates:
		if not candidate.get("appName", ""):
			return candidate
	return None


def getUsableItems(items, currentAppName):
	"""Items whose shortcut would run them in the current app, in settings list order."""
	candidatesByGesture = {}
	for item in items:
		for gesture in item.get("gestures", []):
			candidatesByGesture.setdefault(gesture.lower(), []).append(item)
	usable = []
	for item in items:
		gestures = item.get("gestures", [])
		if gestures and resolveItem(candidatesByGesture[gestures[0].lower()], currentAppName) is item:
			usable.append(item)
	return usable


def getKeyLabel(item):
	gestures = item.get("gestures", [])
	if not gestures:
		return ""
	try:
		label = keyboardHandler.KeyboardInputGesture.fromName(
			formatGestureForDisplay(gestures[0])
		).displayName
	except Exception:
		label = None
	return label if isinstance(label, str) and label else formatGestureForDisplay(gestures[0])


def sortItems(items, order):
	if order == "name":
		return sorted(items, key=lambda item: item.get("name", "").casefold())
	if order == "key":
		return sorted(
			items, key=lambda item: formatGestureForDisplay((item.get("gestures") or [""])[0]).casefold()
		)
	return list(items)


def formatItem(item, browseFormat):
	name = item.get("name", "")
	if browseFormat == "name":
		return name
	key = getKeyLabel(item)
	if browseFormat == "keyName":
		# Translators: Announcement of a browsed item as "shortcut, name", e.g. "g, Open Gmail".
		return _("{key}, {name}").format(key=key, name=name)
	# Translators: Announcement of a browsed item as "name, shortcut", e.g. "Open Gmail, g".
	return _("{name}, {key}").format(name=name, key=key)


def buildHelpText(items, browseFormat):
	lines = [
		# Translators: Usage line at the top of the instant Access browse help.
		_(
			"Up and down arrows or Tab and Shift+Tab: browse items. Enter: run the browsed item. Escape: exit."
		),
		"",
	]
	if not items:
		# Translators: Shown in the browse help when no items can run in the current application.
		lines.append(_("No items are available in this application."))
	lines.extend(formatItem(item, browseFormat) for item in items)
	return "\n".join(lines)
