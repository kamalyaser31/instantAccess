# -*- coding: utf-8 -*-

CONFIG_SECTIONS = [
	"Websites",
	"Programs",
	"Folders",
	"Files",
	"NvdaCommands",
	"TextSnippets",
	"Gestures",
	"Arguments",
	"TextSnippetActions",
	"CommandLabels",
	"RestrictedApps",
	"Settings",
]

TYPE_SECTIONS = ["Websites", "Programs", "Folders", "Files", "NvdaCommands", "TextSnippets"]

# Translators: Item types for instant Access entries.
TYPE_LABELS = [
	_("Website"),
	_("Program"),
	_("Folder"),
	_("File"),
	_("NVDA command"),
	_("Text snippet"),
]

TYPE_TO_LABEL = dict(zip(TYPE_SECTIONS, TYPE_LABELS))

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
