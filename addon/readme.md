# instant Access

## Overview

**Author:** Kamal Yaser  
**Version:** 2026.1  
**Compatibility:** NVDA 2019.3 and later (last tested with 2025.3.2)  
**License:** GNU General Public License v2 or later

instant Access is an NVDA add-on for building your own shortcut layer. You press one gesture to enter instant Access mode, then press the shortcut you assigned to run an item. That item can run one action or multiple actions in sequence, so you can build simple launches or full mini-workflows.

## Built-In Shortcuts

- `NVDA+E`: Toggle instant Access mode on or off.
- `NVDA+Shift+E`: Report the currently focused app name.
- `NVDA+Shift+E` pressed twice quickly: Copy the focused app name to clipboard and announce that it was copied.
- `Escape` (while instant Access mode is active): Exit instant Access mode.

## Where to Configure It

Open NVDA menu, then go to Preferences, Settings, and choose **instant Access**. The settings panel shows your configured items with name, type summary, shortcut, and a short action preview.

From the same panel you can add, edit, delete, and test items. You can also import and export settings, and choose the verbosity level.

## How Items Work

An item is the unit bound to a shortcut. Each item has a name, a gesture, optional app restriction, interval between actions, and an action list.

When the item runs, actions are executed in order from top to bottom. You can reorder actions with Move up and Move down, and you can define delay at two levels: a delay before each action and an interval between actions.

## Creating a New Item

Press **Add** in the settings panel. Enter the item name, assign a shortcut, and decide whether the item should be restricted to a specific app. If restriction is enabled, enter the app name exactly as reported by `NVDA+Shift+E`.

After that, build the actions list. At least one action is required. You can add as many actions as you need and tune delays for each one.

## Action Types

### Website

Use this action to open a URL in the default web browser. The path field stores the URL and runs it directly.

### Program

Use this action to launch an executable file. You can also provide optional command-line arguments for startup flags or profile-specific behavior.

### Folder

Use this action to open a folder path in File Explorer.

### File

Use this action to open a file using the default associated application.

### NVDA Command

Use this action to run an NVDA script or an active add-on script. Choose **Select command** to open the command picker, browse by category, filter commands, and select one command to store in the action.

### Text Snippet

Use this action for reusable text blocks such as template replies, signatures, or frequent command text. Text snippets support three modes:

- **Type:** Simulate typing the text.
- **Copy:** Put the text in clipboard.
- **Paste:** Paste the text through simulated keyboard paste.

If mode is **Type**, you can set **Typing delay** (default `0.05`) to control how fast characters are injected.

## App-Restricted Shortcuts

Shortcuts can be global or app-specific. An app-specific shortcut is only active when that app is focused.

Conflict handling is scope-aware. A global shortcut can reuse the same gesture as an app-specific shortcut without conflict. A conflict is blocked only when the same gesture is duplicated in the same scope: global with global, or same-app with same-app.

When both exist for the same gesture, instant Access prefers the matching app-specific item for the focused app. If there is no matching app-specific item, it falls back to the global one.

## Verbosity

Two verbosity levels are available:

- **Beginner:** fuller spoken feedback.
- **Advanced:** shorter feedback with tones where appropriate.

## Import and Export

You can export the full configuration to a JSON file and import it later on the same or another machine. Import replaces the current configuration.

## Notes and Limits

Reserved gestures are blocked from assignment because they are used internally by instant Access. If no items are configured, toggling instant Access reports that no commands are available.
