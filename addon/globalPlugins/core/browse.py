# -*- coding: utf-8 -*-
"""Pure helpers for browsing items inside the instant Access layer."""

import addonHandler

from .constants import ANNOUNCE_VALUES, TEXT_SNIPPET_ACTION_TO_LABEL, TYPE_TO_LABEL
from .gestures import formatGestureForDisplay, gestureDisplayText, gestureKey, parseAppNames

addonHandler.initTranslation()


def resolveItem(candidates, currentAppName):
	"""Pick the item a gesture runs in the current app: app-specific first, then global."""
	for candidate in candidates:
		if currentAppName in parseAppNames(candidate.get("appName", "")):
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
			candidatesByGesture.setdefault(gestureKey(gesture), []).append(item)
	usable = []
	for item in items:
		gestures = item.get("gestures", [])
		if gestures and resolveItem(candidatesByGesture[gestureKey(gestures[0])], currentAppName) is item:
			usable.append(item)
	return usable


def shouldAnnounceName(item, announceByDefault):
	"""An item's own choice wins over the general setting."""
	choice = item.get("announceName", ANNOUNCE_VALUES[0])
	return announceByDefault if choice == ANNOUNCE_VALUES[0] else choice == ANNOUNCE_VALUES[1]


def getKeyLabel(item):
	gestures = item.get("gestures", [])
	return gestureDisplayText(gestures[0]) if gestures else ""


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


def getItemSearchTokens(item):
	"""Extract searchable text tokens from an item across all its fields."""
	tokens = [
		item.get("name", ""),
		getKeyLabel(item),
		item.get("appName", ""),
	]
	for action in item.get("actions", []):
		actionType = action.get("type", "")
		if actionType:
			tokens.append(actionType)
			tokens.append(TYPE_TO_LABEL.get(actionType, "").replace("&", ""))
		tokens.append(action.get("path", ""))
		tokens.append(action.get("arguments", ""))
		tokens.append(action.get("commandLabel", ""))
		if actionType == "TextSnippets":
			tokens.append(TEXT_SNIPPET_ACTION_TO_LABEL.get(action.get("textAction", ""), ""))
	return " ".join(t for t in tokens if t)


def matchesFilter(item, query):
	"""Multi-word filter matching all words against item tokens, case-insensitively."""
	words = [w.strip().casefold() for w in (query or "").split(" ") if w.strip()]
	if not words:
		return True
	haystack = getItemSearchTokens(item).casefold()
	return all(word in haystack for word in words)
