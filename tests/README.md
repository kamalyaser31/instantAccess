# Regression tests

Run from the repository root:

```powershell
uv sync --frozen
uv run --frozen python -m unittest discover -s tests
uv run --frozen ruff check addon/
uv run --frozen ruff check --isolated --select F821 addon/globalPlugins/core/keyboard
uv run --frozen scons
uv run --frozen scons pot
```

The tests load real core modules and the vendored keyboard library with NVDA,
wx, and keyboard input test doubles. Configuration tests use temporary folders.
The Windows-only batch test launches a temporary echo script through real
`cmd.exe`; it is skipped on other platforms. Other tests do not inject keys or
change the system clipboard. Deliberately induced failures produce expected log
messages; the final unittest result determines success.

Before release, validate in NVDA 2024.1 and the declared tested version:

- Type Unicode text, paste into an editor, and run repeated keystrokes with zero
  and nonzero delays. Run two items rapidly and check their order.
- Test commands that execute scripts and commands that emulate keyboard input,
  including an unavailable command and a failing script, with stop-on-error
  enabled and disabled.
- Test an action from its dialog, switch to the intended target window, and
  verify the preparation delay plus the configured action delay.
- Reload the add-on during a long delay; pending actions must not execute.
- Edit an existing NVDA command and filter the picker; check selection,
  keyboard navigation, and spoken labels with actual wx controls.
- Exercise backup recovery and invalid imports in a disposable NVDA profile.

The queue serializes add-on actions. Starting an external program or sending
keys does not prove that the target application has finished processing them;
use configured delays where the target requires time. Cancellation is
cooperative and cannot undo input already sent or interrupt an OS call or
NVDA script already running.
