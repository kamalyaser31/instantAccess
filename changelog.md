# Changelog

## [2026.4] - 2026-07-07
### Added
- New Feature: Keystrokes macro simulation (allows advanced screen reader users to execute keyboard shortcut sequences with custom delays).
- Documentation: Added complete user guides and macro examples for the new Keystrokes feature in English and Arabic readmes.

### Changed
- Code Quality: Refactored core modules (`plugin.py`, `executor.py`, `item_dialog.py`) to eliminate code duplication and align with clean code standards.

## [2026.3] - 2026-05-07
### Added
- Official release update.
- Fully updated the Arabic user guide to provide clearer instructions and information.

### Fixed
- Resolved a critical issue that prevented the add-on from loading correctly in certain NVDA environments.

### Changed
- Internal refinements and cleanup to ensure smoother performance.

# Changes Since "Updated Readme" (c1bf430)

This document outlines all technical and functional changes made to the **instantAccess** add-on since the commit `c1bf430` (updated readme).

## [Summary of Changes]

### 🏗️ Architectural & Core Improvements
- **Logging System:** Integrated `logging` module across `config_manager.py`, `executor.py`, and `plugin.py` for professional debugging and error tracking.
- **Robust Exception Handling:** Refined `try-except` blocks to catch specific errors (e.g., `ValueError`, `TypeError`, `KeyError`) instead of generic exceptions, improving stability.
- **Code Documentation:** Added extensive docstrings and comments to core classes and functions for better maintainability.

### ⚙️ Configuration Management (`config_manager.py`)
- **Enhanced Data Validation:** Added strict type checking and default values for `typingDelay` and `delay` parameters.
- **Improved Item Conversion:** Added error logging during the conversion of stored items to public formats.
- **Refined Conflict Detection:** Optimized `findGestureConflict` logic with better normalization of gestures and application names.

### 🚀 Execution Engine (`executor.py`)
- **Cross-Platform Support:** Added preliminary support for opening folders on Linux (via `xdg-open`) and macOS (via `open`), although the primary target remains Windows.
- **Clipboard Reliability:** Improved `_setClipboardText` to handle errors gracefully using internal logging.
- **Execution Flow:** Optimized `executeInstantItem` to handle interval and delay calculations more reliably.

### 🔌 Plugin Logic (`plugin.py`)
- **Resource Management:** Improved the termination process (`terminate`) to safely remove settings panels and shutdown the thread pool executor.
- **Gesture Handling:** Refined the `getScript` wrapper to ensure the "Instant Layer" is always finished correctly, preventing the UI from getting stuck.
- **Dynamic Configuration:** Better handling of dynamic configuration changes and toggle gestures.

### 🌍 Localization & Documentation
- **Updated Translations:** Significant updates to the English localization (`nvda.po`), including new strings for settings and error messages.
- **Redundant File Cleanup:** Removed outdated HTML and Markdown readme files from the `addon/doc/en/` directory in favor of the root `readme.md`.

---
*Generated automatically by Gemini CLI.*
