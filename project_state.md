# Project State: instantAccess

## Overview
- **Name:** instantAccess
- **Type:** NVDA Add-on
- **Version:** 2026.6
- **Repository:** https://github.com/kamalyaser31/instantAccess
- **Target NVDA Versions:** Minimum 2024.1.0, Last Tested 2026.1

## Architecture & Tooling
- **Build System:** SCons 4.10.1 (`sconstruct` + `site_scons/` containing `NVDATool` and `gettexttool`).
- **Package & Dependency Manager:** `uv` with PEP 735 dependency groups (`build`, `l10n`, `lint`, `dev`) and locked with `uv.lock`.
- **Linting & Code Quality:** `ruff` (formatting & fast linting directly via `uv run ruff check addon/`).
- **CI/CD:** Lightweight GitHub Actions workflow in `.github/workflows/build_addon.yml` running regression test discovery and undefined-name checks on vendored dependencies.

## Key Files
- `addon/`: Add-on core logic, UI, globalPlugins, documentation, and localization.
- `buildVars.py`: Add-on metadata, manifest configurations, and resource declarations (including `speechDictionaries`, `symbolDictionaries`, `brailleTables`).
- `sconstruct`: SCons build orchestrator.
- `pyproject.toml`: Modern project declaration and dependency groups.
- `uv.lock`: Pinned reproducible dependencies.
- `.github/workflows/build_addon.yml`: CI/CD automation for PRs, branch pushes, and tag releases.
- `tests/`: 41 automated regression tests and isolated stubs (`test_config.py`, `test_dialogs.py`, `test_execution.py`).

## Pending Work
- Version 2026.7 is planned in `plan-2026.7.md`. M1 to M2d are done in the working tree (2026-11-04): the cleanup, four bug fixes, the simplification, the NVDA practice fixes, and the keyboard library trim. They are committed on the local branch `feat/2026.7` (not pushed, not merged into main) and not tested in live NVDA. The readme license line from M2d.1 moved to M4. M3 (twelve refinements) waits for Kamal.
- Interfaces after M2:
  - Gesture lookups use `gestures.gestureKey` (`inputCore.normalizeGestureIdentifier`), and the layer reads `gesture.normalizedIdentifiers`.
  - `gestures.gestureDisplayText` gives NVDA's localized key names.
  - `gestures.getAddonGestures` reads the add-on's own gestures.
  - `ConfigManager.saveItem(oldName, ...)` replaces `addItem` and `updateItem`.
  - `ConfigManager` keeps the normalized config in memory until a save or `replaceConfig` (import).
  - `config_io` writes only when `NVDAState.shouldWriteToDisk()` allows it; otherwise it raises `DiskWriteDisabledError`.
  - `constants.ACTION_FIELDS` maps each action type to its stored key.
  - `item_dialog._labeledRow` builds every labeled row: label first, in one flat sizer.
  - `parseDelayField` and `actionDetails` are shared module functions.
  - Every module logs through `logHandler.log`, and each message starts with "instantAccess:".
  - The NVDA command picker loads the commands on the main thread.
- Keyboard library: three files, not the two the plan said. `__init__.py` holds `send` and `write`, `_winkeyboard.py` keeps only the sending code, `_canonical_names.py` is unchanged, and the MIT text is in `LICENSE.txt`. `_winkeyboard.py` stays separate because the tests replace it with a stand-in and CI runs on Linux, where `ctypes.WinDLL` does not exist.
- Shared helpers `actionsNeedSwitchDelay` and `confirmSwitchDelay` in `item_dialog.py` serve both Test buttons. `queueRunItemExecution(item, preDelay=0)` passes the delay to the queue.
- Edit Python files by script, not with the Edit tool. The workspace hook runs black on edited files, and black replaces this project's tab indentation (ruff format, `indent-style = "tab"`). Working copies mix CRLF and LF per file, so keep each file's line endings.
- M2.4 (gesture normalization bug) and M2b (simplification, about 350 lines) were added after checking the NVDA source at `E:\github\nvda\source` (2026.3 beta) and the `release-2024.1` tag. Rejected: capturing shortcuts with `inputCore.manager._captureFunc`, because it is a private NVDA name. M2c (six NVDA practice fixes) followed a review against the skill checklist.
- Kept on purpose: `gui.messageBox`, because `MessageDialog` is missing in NVDA 2024.1; the vendored `keyboard` library (boppreh/keyboard 0.13.5, MIT, already modified here), because NVDA's key names differ from the saved Keystrokes names. M2d trims it to what `send` and `write` need, and adds the missing MIT notice; settings in the add-on's JSON file, so export includes them; and no merged modules.
- The build excludes `*.pyc` and `__pycache__/*` (`buildVars.excludedFiles`). The package has 33 files.
- Decisions (2026-11-04): M3.3 reads `gui.mainFrame.prevFocus` instead of adding `event_foreground`. No `speakOnDemand` on the add-on's scripts.
- Decisions: Programs actions keep launching a new instance (no "switch to window" option). Named buffers (#22) and `Space`+key describe (#20) are out of scope. Letter shortcuts work under the Arabic layout, so no layout handling is needed.
- `tests/` now has 64 tests (`test_browse.py` included). `tests/nvda_stubs.py` also stubs `NVDAState`, `logHandler`, and `inputCore.normalizeGestureIdentifier`, which is a copy of NVDA's algorithm.

## Recent Changes (2026-09-24 - Version 2026.6)
- Merged PR #18 fixing configuration recovery, action ordering, and execution failure handling.
- Serialized execution: Introduced `ExecutionQueue` (bounded 32-slot queue, single worker) for serializing shortcuts and action tests without keyboard/clipboard races.
- NVDA script synchronization: Synchronous wait on worker thread with main thread dispatch (`wx.CallAfter`) and timeout handling, preserving repeat-count identity (`__func__`).
- Configuration disaster recovery & atomic safety: Prevented overwriting backups with corrupt configurations, recovered missing configurations from existing backups, strictly validated data before saving, and preserved zero delays.
- Win32 & system execution fixes: Fixed key-name buffer capacity in Win32 API (`len(name_buffer)`), fixed Windows batch script quoting for spaced paths, and added safe `SystemRoot` fallback.
- Test suite: Added 41 automated regression tests and dedicated CI checks.
- Upgraded the build system and tooling to modern standards (PEP 735, `uv`, `uv.lock`, and upgraded GitHub Actions workflows).
- Purged vendored keyboard library non-Windows code and dead POSIX code.
- Added Item Duplication (`Duplicate` button) with unique naming.
- Added isolated Action Testing with 3-second preparation countdown for typing and keystrokes.
- Added multi-action Stop on Error execution safety.
- Added keyboard navigation ergonomics (`Enter` to edit, `Delete` to delete, `Ctrl+Up`/`Ctrl+Down` to reorder).
- Added support for PATH commands, `.bat`/`.cmd` scripts, custom URI schemes, and quote stripping.
- Added atomic configuration saving, automatic `.bak` backups, and corrupted configuration recovery prompts.
- Added native Arabic markdown documentation (`addon/doc/ar/readme.md`).
- Published official GitHub Release `v2026.5` with asset `instantAccess-2026.5.nvda-addon`.
- Submitted registration issue to NV Access Add-on Store (`nvaccess/addon-datastore#11721`), successfully validated and accepted for official catalog publication.
- Purged obsolete tracked binary and generated artifacts (`instantAccess-2026.4.nvda-addon`, compiled `.mo` files, `.vscode/`, and generated `.html` / `manifest.ini` files).
- Streamlined developer tooling: eliminated `prek`, `pyright`, and nodejs dependencies, adopting a lightweight setup with direct `ruff` linting and fast CI/CD builds.
