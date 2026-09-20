# Project State: instantAccess

## Overview
- **Name:** instantAccess
- **Type:** NVDA Add-on
- **Version:** 2026.4
- **Repository:** https://github.com/kamalyaser31/instantAccess
- **Target NVDA Versions:** Minimum 2024.1.0, Last Tested 2026.1

## Architecture & Tooling
- **Build System:** SCons 4.10.1 (`sconstruct` + `site_scons/` containing `NVDATool` and `gettexttool`).
- **Package & Dependency Manager:** `uv` with PEP 735 dependency groups (`build`, `l10n`, `lint`, `dev`) and locked with `uv.lock`.
- **Linting & Code Quality:** `ruff` (formatting & linting) + `prek` (Rust-based Git hooks in `prek.toml`).
- **Type Checking:** `pyright` configured in `pyproject.toml`.
- **CI/CD:** GitHub Actions workflow in `.github/workflows/build_addon.yml` using `astral-sh/setup-uv@v10.1.0` and official GitHub Actions v7.

## Key Files
- `addon/`: Add-on core logic, UI, globalPlugins, documentation, and localization.
- `buildVars.py`: Add-on metadata, manifest configurations, and resource declarations (including `speechDictionaries`, `symbolDictionaries`, `brailleTables`).
- `sconstruct`: SCons build orchestrator.
- `pyproject.toml`: Modern project declaration and dependency groups.
- `prek.toml`: Git commit hooks.
- `uv.lock`: Pinned reproducible dependencies.
- `.github/workflows/build_addon.yml`: CI/CD automation for PRs, branch pushes, and tag releases.

## Recent Changes (2026-09-20)
- Upgraded the build system, typings, and tooling from legacy `pre-commit` to `addonTemplate` (PEP 735, `uv`, `prek.toml`, `uv.lock`, and upgraded GitHub Actions workflows).
- Verified build and translation generation via `uv run scons` and `uv run scons pot`.
