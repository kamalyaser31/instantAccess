# Project State: instantAccess

## Overview
- **Name:** instantAccess
- **Type:** NVDA Add-on
- **Version:** 2026.7 (released 2026-11-09)
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
- `tests/`: 105 automated regression tests and isolated stubs (`test_browse.py`, `test_config.py`, `test_dialogs.py`, `test_execution.py`).

## Pending Work
- Version 2026.7 is planned in `plan-2026.7.md`. M1 to M2d are done in the working tree (2026-11-04): the cleanup, four bug fixes, the simplification, the NVDA practice fixes, and the keyboard library trim. They are committed on the local branch `feat/2026.7` (not pushed, not merged into main). They passed a live test in portable NVDA 2026.2 on 2026-11-04. That test found the old M2.5 bug: Shift with navigation keys selected nothing, because `_winkeyboard._send_event` never set `KEYEVENTF_EXTENDEDKEY`. The fix is committed and passed live in portable NVDA: `EXTENDED_VKS` (Page Up/Down, End, Home, arrows, Insert, Delete) get the flag on press and release. Ten M3 items and the fixes from their review are committed on `feat/2026.7` (2026-11-05), and they passed Antigravity's live test in portable NVDA 2026.2 (a real run as administrator and the full import flow were not exercised); M3.2, M3.6 and M3.8 are reviewed and committed (`0f8f178`), and only their live test is left.
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
- `placeholders.findOnPath` falls back to the PATH stored in the registry, because other add-ons can replace `os.environ["PATH"]` (Acapela `globalPlugins/menu.py` does). Kamal confirmed the fix live in portable NVDA with Acapela on 2026-11-07. Use it for every program lookup, never bare `shutil.which`. Tests: 106.
- Decision (2026-11-07): conditions (if and else) are deferred until a real need appears; the design is in `plan-2026.8.md`.
- Add keystroke opens `KeystrokeRecordDialog` (2026-11-08): it records keys until Escape, `executor.addRecordedKeystroke` merges a repeated key into a count (`down 3`), and Ctrl, Alt or Shift alone is recorded when the next key shows it was released alone, because wx sends no key-up to this dialog (an EVT_KEY_UP attempt failed live on 2026-11-08). Kamal confirmed Ctrl and Alt alone live on 2026-11-08. Tests: 107. Taken from nvdaMacroManager; stopping keys when the foreground program changes is planned for a later release.
- Keyboard library: three files, not the two the plan said. `__init__.py` holds `send` and `write`, `_winkeyboard.py` keeps only the sending code, `_canonical_names.py` is unchanged, and the MIT text is in `LICENSE.txt`. `_winkeyboard.py` stays separate because the tests replace it with a stand-in and CI runs on Linux, where `ctypes.WinDLL` does not exist.
- Shared helpers `actionsNeedSwitchDelay` and `confirmSwitchDelay` in `item_dialog.py` serve both Test buttons. `queueRunItemExecution(item, preDelay=0)` passes the delay to the queue.
- Edit Python files by script, not with the Edit tool. The workspace hook runs black on edited files, and black replaces this project's tab indentation (ruff format, `indent-style = "tab"`). Working copies mix CRLF and LF per file, so keep each file's line endings.
- M2.4 (gesture normalization bug) and M2b (simplification, about 350 lines) were added after checking the NVDA source at `E:\github\nvda\source` (2026.3 beta) and the `release-2024.1` tag. Rejected: capturing shortcuts with `inputCore.manager._captureFunc`, because it is a private NVDA name. M2c (six NVDA practice fixes) followed a review against the skill checklist.
- Kept on purpose: `gui.messageBox`, because `MessageDialog` is missing in NVDA 2024.1; the vendored `keyboard` library (boppreh/keyboard 0.13.5, MIT, already modified here), because NVDA's key names differ from the saved Keystrokes names. M2d trims it to what `send` and `write` need, and adds the missing MIT notice; settings in the add-on's JSON file, so export includes them; and no merged modules.
- The build excludes `*.pyc` and `__pycache__/*` (`buildVars.excludedFiles`). The package has 33 files.
- Decisions (2026-11-04): No `speakOnDemand` on the add-on's scripts.
- Decisions: Programs actions keep launching a new instance (no "switch to window" option). Named buffers (#22) and `Space`+key describe (#20) are out of scope. Letter shortcuts work under the Arabic layout, so no layout handling is needed.
- New interfaces: `ConfigManager.moveItem(name, step)`; `plugin.event_foreground` remembers the last non-NVDA app, and the item dialog reads it through `InstantAccessSettingsPanel.getPreviousAppName`, because NVDA clears `prevFocus` right after showing the settings dialog; Programs actions store `data["runAsAdmin"]` only when true; `executor._getClipboardText`, `PASTE_SETTLE_SECONDS`; items store `enabled` and `announceName` (`default`, `on`, `off`) only when not the default; `settings.announceName` is the general switch; `browse.shouldAnnounceName` decides; `ExecutionQueue.submit(item, preDelay, announce)` takes the result; `buildInstantGestures` drops disabled items; `settings_panel.refreshList` keeps only the filtered items in `self.items`; `gestures.parseAppNames` and `appNamesConflict` handle the comma list stored in `appName` (Arabic comma too); `gestures.gestureToKeystroke` and `executor.isValidKeystroke` serve the Add keystroke button; `ConfigManager.mergeItems(imported)` returns (added, skipped) and reuses `findGestureConflict`; a merge leaves the panel's unsaved settings alone; `refreshList(selectName)` clears a filter that would hide the saved item.
- `tests/nvda_stubs.py` stubs `NVDAState`, `logHandler`, `textInfos`, `inputCore.normalizeGestureIdentifier`, and wx dialog/menu controls.
- Kamal ran the M5 list himself in portable NVDA 2026.2 on 2026-11-07, and everything worked. He also confirmed it works on his installed 2025.3.2, so it may be merged. `feat/2026.7` is pushed to GitHub, not merged into main. M4 is done and committed (2026-11-07): readmes, version, changelogs, template, Arabic strings (the app says "تصفية" for Filter, so the Arabic readme does too). The en and zh_CN catalogs are merged only. Next is M5.
- Both guides were rewritten on 2026-11-07: first item, daily use, eight examples, then the reference, with the same matter in English and Arabic. The zh_CN guide keeps the old structure. The build has no fenced code extension (`buildVars.markdownExtensions` is empty), so guides use lists for multi-line values.
- M3 is fully implemented on `feat/2026.7`: M3.2 (`HelpListDialog` with multi-field incremental search and item activation), M3.6 (per-run cancellation via `ExecutionQueue.cancelCurrent()` on `NVDA+E`), and M3.8 (context read on the main thread when the item starts, only if needed, in `executor._captureContextOnMainThread`; Shell.Application needs `dynamic=True`; batch check resolves the PATH; `placeholders` module with `{date}`, `{time}`, `{clipboard}`, `{selection}`, `{file}`, `{folder}`, escaping `{{`/`}}`, batch argument rejection, context validation, and the "Insert variable…" menu). All 105 tests pass.

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
