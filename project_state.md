# Project State: instantAccess

## Overview
- **Name:** instantAccess
- **Type:** NVDA Add-on
- **Version:** 2026.5
- **Repository:** https://github.com/kamalyaser31/instantAccess
- **Target NVDA Versions:** Minimum 2024.1.0, Last Tested 2026.1

## Architecture & Tooling
- **Build System:** SCons 4.10.1 (`sconstruct` + `site_scons/` containing `NVDATool` and `gettexttool`).
- **Package & Dependency Manager:** `uv` with PEP 735 dependency groups (`build`, `l10n`, `lint`, `dev`) and locked with `uv.lock`.
- **Linting & Code Quality:** `ruff` (formatting & fast linting directly via `uv run ruff check addon/`).
- **CI/CD:** Lightweight GitHub Actions workflow in `.github/workflows/build_addon.yml` using `astral-sh/setup-uv@v10.1.0` and official GitHub Actions v7.

## Key Files
- `addon/`: Add-on core logic, UI, globalPlugins, documentation, and localization.
- `buildVars.py`: Add-on metadata, manifest configurations, and resource declarations (including `speechDictionaries`, `symbolDictionaries`, `brailleTables`).
- `sconstruct`: SCons build orchestrator.
- `pyproject.toml`: Modern project declaration and dependency groups.
- `uv.lock`: Pinned reproducible dependencies.
- `.github/workflows/build_addon.yml`: CI/CD automation for PRs, branch pushes, and tag releases.

## Recent Changes (2026-09-20)
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
