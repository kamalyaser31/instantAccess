# -*- coding: utf-8 -*-

import addonHandler

addonHandler.initTranslation()

TYPE_SECTIONS = ["Websites", "Programs", "Folders", "Files", "NvdaCommands", "TextSnippets", "Keystrokes"]

# Translators: Item types for instant Access entries.
TYPE_LABELS = [
	# Translators: Action type that opens a website or URI.
	_("Website"),
	# Translators: Action type that starts a program.
	_("Program"),
	# Translators: Action type that opens a folder.
	_("Folder"),
	# Translators: Action type that opens a file.
	_("File"),
	# Translators: Action type that runs an NVDA command.
	_("NVDA command"),
	# Translators: Action type that types, copies or pastes text.
	_("Text snippet"),
	# Translators: Action type that sends a sequence of key presses.
	_("Keystrokes"),
]

TYPE_TO_LABEL = dict(zip(TYPE_SECTIONS, TYPE_LABELS))

# The stored data key that holds each action type's main value (shown as "path" in the dialogs).
ACTION_FIELDS = {
	"Websites": "url",
	"Programs": "path",
	"Folders": "path",
	"Files": "path",
	"NvdaCommands": "commandId",
	"TextSnippets": "text",
	"Keystrokes": "keys",
}

TEXT_SNIPPET_ACTION_VALUES = ("type", "copy", "paste")

# Translators: Action labels for text snippet entries.
TEXT_SNIPPET_ACTION_LABELS = [_("Type the text"), _("Copy"), _("Paste")]

TEXT_SNIPPET_ACTION_TO_LABEL = dict(zip(TEXT_SNIPPET_ACTION_VALUES, TEXT_SNIPPET_ACTION_LABELS))

RESERVED_GESTURES = {"kb:escape", "kb:nvda+e", "kb:nvda+shift+e"}

# Translators: Category name for the instant Access add-on.
CATEGORY_LABEL = _("instant Access")

# Translators: Description for the toggle instant mode command in Input Gestures.
TOGGLE_DESCRIPTION = _("Toggle instant Access mode.")

# Translators: Description for reporting the currently focused application name.
REPORT_APP_NAME_DESCRIPTION = _("Report current app name.")

# Default gestures of the add-on's own scripts, used when Input Gestures has no mapping.
ADDON_SCRIPT_GESTURES = {
	TOGGLE_DESCRIPTION: ["kb:NVDA+e"],
	REPORT_APP_NAME_DESCRIPTION: ["kb:NVDA+shift+e"],
}

# Translators: Caption for error message dialogs.
ERROR_CAPTION = _("Error")

# Translators: Caption for confirmation dialogs.
CONFIRM_CAPTION = _("Confirm")

ALL_FILES_WILDCARD = "All files (*.*)|*.*"

# Translators: Label for beginner verbosity level.
VERBOSITY_BEGINNER = _("Beginner")

# Translators: Label for advanced verbosity level.
VERBOSITY_ADVANCED = _("Advanced")

VERBOSITY_VALUES = ("beginner", "advanced")

BROWSE_FORMAT_VALUES = ("nameKey", "keyName", "name")

# Translators: Choices for how items are announced while browsing the instant Access layer.
BROWSE_FORMAT_LABELS = [_("Name, then shortcut"), _("Shortcut, then name"), _("Name only")]

BROWSE_ORDER_VALUES = ("list", "name", "key")

# Translators: Choices for the order of items while browsing the instant Access layer.
BROWSE_ORDER_LABELS = [_("Settings list order"), _("Alphabetical by name"), _("By shortcut")]

DEFAULT_SETTINGS = {
	"verbosity": VERBOSITY_VALUES[0],
	"browseEnabled": False,
	"browseFormat": BROWSE_FORMAT_VALUES[0],
	"browseOrder": BROWSE_ORDER_VALUES[0],
}

# Layer keys used for browsing, mapped to the plugin script that handles them.
BROWSE_GESTURES = {
	"kb:downArrow": "browseNext",
	"kb:tab": "browseNext",
	"kb:upArrow": "browsePrevious",
	"kb:shift+tab": "browsePrevious",
	"kb:enter": "browseActivate",
	"kb:numpadEnter": "browseActivate",
	"kb:f1": "browseHelp",
	"kb:h": "browseHelp",
}
