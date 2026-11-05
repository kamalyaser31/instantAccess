# Task: instantAccess 2026.7

The full scope is in [plan-2026.7.md](plan-2026.7.md). M1 to M2d are done in the working tree (2026-11-04). They are committed on the local branch `feat/2026.7` (not pushed, not merged into main), and they passed the portable NVDA 2026.2 test; Kamal's installed NVDA is not tested yet. The readme license line from M2d.1 moved to M4.

- [ ] M3 Refinements (on hold until Kamal says to start): F1 list runs and filters items; NVDA+E stops a running item; variables (6) with the "Insert variable…" menu
- [ ] Live checks left for the ten M3 items: a real run as administrator, the full import flow through the file dialog, and Add keystroke under the Arabic layout; the rest passed in portable NVDA on 2026-11-05
- [ ] M4 Release preparation: docs (the readmes must cover these ten, with the keyboard library license line left over from M2d.1, via readme-writer), translations (msgmerge the .po files against the new template), version 2026.7, changelog, tests, build
- [ ] M5 Live NVDA test (ask Kamal first: it closes his installed NVDA)
