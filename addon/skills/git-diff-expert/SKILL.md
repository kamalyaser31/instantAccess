---
name: git-diff-expert
description: Expert in comparing Git commits, extracting functional changes, and generating high-quality changelogs. Use this skill when the user asks to "compare two commits", "generate a changelog from diff", or "analyze changes between versions".
---

# Git Diff Expert Skill

This skill specializes in analyzing the differences between two Git commit references and transforming the technical diff into a human-readable, professional changelog.

## Core Capabilities

- **Commit Comparison:** Accurately identifies changes between any two Git references (hashes, tags, branches).
- **Change Categorization:** Automatically classifies changes into logical groups:
  - 🚀 **Features:** New functionality or enhancements.
  - 🐛 **Bug Fixes:** Resolved issues and stability improvements.
  - 🏗️ **Refactoring:** Code cleanup, architectural changes, and internal optimizations.
  - 🌍 **Localization:** Updates to translation files or multi-language support.
  - 📝 **Documentation:** Updates to readme, manuals, or inline comments.
- **Deep Analysis:** Looks beyond file stats to understand the functional impact of code changes.
- **Professional Formatting:** Produces clean, Markdown-formatted reports suitable for release notes.

## Workflow Instructions

When this skill is triggered:

1. **Identify References:** Confirm the two Git references to compare (e.g., `HEAD^..HEAD` or `v1.0..v1.1`).
2. **Technical Extraction:**
   - Run `git diff <ref1>..<ref2> --stat` to get a high-level overview.
   - Run `git diff <ref1>..<ref2> <path>` for critical files to understand logic changes.
3. **Synthesis & Categorization:**
   - Analyze commit messages in the range: `git log <ref1>..<ref2> --oneline`.
   - Map technical changes to user-facing benefits.
4. **Generate Report:**
   - Create a Markdown file (e.g., `CHANGELOG_UPDATE.md`).
   - Use professional headers and bullet points.
   - Include a "Summary of Changes" section.

## Rules of Engagement

- **Be Precise:** Don't hallucinate features; only report what's in the diff.
- **Tone:** Professional, direct, and senior engineer-oriented.
- **Context Awareness:** In this project, prioritize changes in `addon/globalPlugins/core/` and translation files (`.po`).
- **Safety:** Never expose sensitive data or internal keys if found in the diff.

## Example Usage

**User Prompt:** "Compare the last 3 commits and write a changelog."
**Action:** Use `HEAD~3..HEAD`, analyze, and write to file.

**User Prompt:** "What changed since the last release tag?"
**Action:** Find the last tag using `git describe --tags --abbrev=0`, compare with `HEAD`, and report.

---
*Developed by Gemini CLI Git Expert.*
