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
