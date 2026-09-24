# Changelog

All notable changes to the **instantAccess** add-on will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Preserve valid backups during recovery, recover missing configuration files, and leave disk data intact when recovery is declined or fails.
- Reject malformed imports without silently discarding items, retain zero delays, and reject non-finite timing values.
- Serialize shortcuts and action tests through one bounded queue; cancel pending work and interrupt delays when the add-on terminates.
- Wait for NVDA commands to finish their script before continuing, and correctly apply stop-on-error handling to script, keyboard, and browser failures.
- Restore text typing, release keyboard state after failures, and correct the Windows key-name buffer capacity.
- Correct Windows batch file quoting and argument handling for paths containing spaces.
- Apply action delays during testing, preserve command-picker selections, and safely handle secure-mode initialization.
- Keep duplicated item names unique beyond 999 copies and retain dialog data when saving fails.

### Added
- Automated regression tests and a separate undefined-name check for the vendored keyboard library in CI.

## [2026.5] - 2026-09-20

### Added
- **Item Duplication**: Added a `Duplicate` button in the main Settings Panel to clone existing items with all their actions and settings under an auto-incremented unique name (`Name (copy)`), clearing the shortcut to avoid immediate conflict.
- **Individual Action Testing**: Added a `Test` button inside the Action Dialog to test single actions directly. Keystrokes and typing actions include an automated 3-second preparation delay and confirmation prompt to allow blind users to switch (`Alt+Tab`) to the target window safely.
- **Stop on Error Execution**: Added a dedicated option for multi-action items to immediately abort remaining actions in the sequence if any action fails.
- **Keyboard Ergonomics**:
  - Pressing `Enter` on an item in the Settings Panel immediately opens the edit dialog.
  - Pressing `Delete` on an item or action opens a confirmation dialog to delete it.
  - Pressing `Ctrl+Up` / `Ctrl+Down` reorders actions inside the item dialog.
- **Enhanced System Integration**:
  - Automatic lookup of executables found in the system `PATH` (e.g. `cmd`, `notepad`, `calc`, `code`) via `shutil.which`.
  - Native execution support for batch files (`.bat` and `.cmd`) using Windows shell dispatching.
  - Support for custom URI schemes (e.g. `mailto:`, `ms-settings:`) without prepending default web schemes.
  - Automatic stripping of surrounding double and single quotes from paths upon saving and execution.
- **Non-blocking Path Validation**: Added an accessible confirmation prompt when saving an action if the path is not found on disk or in `PATH`, allowing the user to proceed or revise.
- **Safe Settings Import/Export**:
  - Added a confirmation prompt before importing settings to prevent accidental overwrites of existing configurations.
  - Added accessible notifications upon successful import and export.
- **Disaster Recovery & Atomic Configuration**:
  - Implemented atomic file saving (`.tmp` file creation followed by atomic replacement) to prevent file corruption during unexpected power loss.
  - Automatic backup creation (`config.json.bak`) upon every successful configuration save.
  - Startup corruption detection with a recovery dialog offering to restore the backup automatically.
- **Native Arabic Documentation**: Added `addon/doc/ar/readme.md` so that localized HTML documentation (`readme.html`) is compiled automatically by SCons during builds.

### Changed
- **Settings Panel Column**: Renamed Column 3 from "Path" to "Details" to accurately represent multi-action summaries.
- **Action Dialog Label**: Clarified the delay label to "Delay before executing this action (seconds)".
- **Modernized Build Infrastructure**: Upgraded to official NVDA `addonTemplate` 2025/2026 standards, adopting PEP 735 dependency groups in `pyproject.toml`, `uv`, `prek.toml` for ultra-fast Git hooks, and modern GitHub Actions workflows.
- **Vendored Library Cleanup**: Streamlined the vendored `keyboard` library by removing unused non-Windows platform code (`_darwinkeyboard.py`, `_nixkeyboard.py`, etc.) and test suites, significantly reducing add-on size.
- **POSIX Code Elimination**: Purged dead POSIX/Darwin fallback code from `executor.py`.

### Fixed
- **Entrypoint Export**: Fixed critical `GlobalPlugin` export in `instantAccess.py` ensuring NVDA discovers and loads the plugin reliably.
- **Resource Management**: Properly cleared `configManager` references, UI callbacks, and running executor threads upon plugin termination.
- **Empty App Name Feedback**: Spoke an accessible error message when the current application name cannot be determined via `NVDA+Shift+E`.
- **Localization Correction**: Corrected an erroneous translation for app restriction in the Arabic `.po` catalog.

## [2026.4] - 2026-07-07

### Added
- **Keystrokes Macro Simulation**: Added simulation of keystroke sequences with custom intervals, allowing screen reader users to automate keyboard navigation workflows.
- **Documentation**: Added complete user guides and macro examples for the Keystrokes feature in English and Arabic documentation.

### Changed
- **Code Quality**: Refactored core modules (`plugin.py`, `executor.py`, `item_dialog.py`) to eliminate code duplication and align with clean code standards.

## [2026.3] - 2026-05-07

### Added
- Official release update.
- Fully updated the Arabic user guide to provide clearer instructions and information.

### Fixed
- **Add-on Loading**: Resolved a critical issue that prevented the add-on from loading correctly in certain NVDA environments.

### Changed
- Internal stability refinements and cleanup to ensure smoother performance.
