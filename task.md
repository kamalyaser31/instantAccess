# Task: instantAccess 2026.7

The full scope is in [plan-2026.7.md](plan-2026.7.md). M1 to M2d are done in the working tree (2026-11-04). They are committed on the local branch `feat/2026.7` (not pushed, not merged into main), and they passed the portable NVDA 2026.2 test; Kamal's installed NVDA is not tested yet. The readme license line from M2d.1 moved to M4.

- [ ] zh_CN strings and guide: 2026.7 shipped without them on 2026-11-09 because the translator was late. Their update (issue #25) goes into the next release, with a thank-you line in the changelog.
- [ ] Later release: stop keystrokes and typing when the foreground program changes (idea from nvdaMacroManager; compare process, not window, because Shift+F10 opens a menu window).
