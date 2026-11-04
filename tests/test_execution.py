import ast
import ctypes
import os
from pathlib import Path
import queue
import subprocess
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import Mock, patch

from nvda_stubs import ROOT, ex, keyboard, backend, wx, plugin, gv
import auditcore.nvda_commands as commands


class ExecutionTests(unittest.TestCase):
	def setUp(self):
		self.mainQueue = queue.Queue()
		self.scriptQueue = queue.Queue()
		self.messages = []
		self.patches = [
			patch.object(wx, "CallAfter", side_effect=lambda fn, *a, **kw: self.mainQueue.put((fn, a, kw))),
			patch.object(
				wx, "IsMainThread", side_effect=lambda: threading.current_thread() is threading.main_thread()
			),
			patch.object(ex, "queueMessage", side_effect=self.messages.append),
		]
		for p in self.patches:
			p.start()
		self.addCleanup(patch.stopall)

	def runPending(self, workQueue):
		while not workQueue.empty():
			fn, args, kwargs = workQueue.get_nowait()
			fn(*args, **kwargs)

	def pump(self, future):
		deadline = time.monotonic() + 3
		while not future.done() and time.monotonic() < deadline:
			self.runPending(self.mainQueue)
			self.runPending(self.scriptQueue)
			time.sleep(0.001)
		return future.result(timeout=1)

	def runner(self):
		runner = ex.ExecutionQueue()
		self.addCleanup(runner.shutdown)
		return runner

	def installScriptHost(self):
		def execute(script, gesture):
			try:
				script(gesture)
			except Exception:
				pass  # NVDA logs and consumes exceptions.

		patch.object(commands.scriptHandler, "executeScript", side_effect=execute, create=True).start()
		patch.object(
			commands.scriptHandler,
			"queueScript",
			side_effect=lambda script, gesture: self.scriptQueue.put((gesture.executeScript, (script,), {})),
			create=True,
		).start()

	def test_typing_uses_real_vendor_without_name_error(self):
		backend.type_unicode.reset_mock()
		self.assertTrue(
			ex.executeInstantAction({"type": "TextSnippets", "path": "abc", "typingDelay": 0})
		)
		self.assertEqual([c.args[0] for c in backend.type_unicode.call_args_list], list("abc"))

	def test_invalid_keystroke_is_a_normal_failure(self):
		with patch.object(keyboard, "parse_hotkey", side_effect=ValueError("unknown key")):
			self.assertFalse(ex.executeInstantAction({"type": "Keystrokes", "path": "bad", "pressDelay": 0}))
		self.assertIn("Could not send keystroke", self.messages[-1])

	def test_send_releases_pressed_keys_after_os_failure(self):
		with (
			patch.object(keyboard, "parse_hotkey", return_value=(((1,), (2,)),)),
			patch.object(backend, "press", side_effect=[None, OSError("blocked")]),
			patch.object(backend, "release") as release,
		):
			with self.assertRaises(OSError):
				keyboard.send("ctrl+a")
			release.assert_called_once_with(1)

	def test_typing_stops_when_cancelled(self):
		cancel = threading.Event()
		with patch.object(backend, "type_unicode", side_effect=lambda letter: cancel.set()) as typed:
			self.assertFalse(keyboard.write("abc", delay=60, cancel_event=cancel))
			typed.assert_called_once_with("a")

	def test_line_breaks_are_sent_as_keys(self):
		with (
			patch.object(keyboard, "send") as send,
			patch.object(backend, "type_unicode") as typed,
		):
			self.assertTrue(keyboard.write("a\nb"))
		send.assert_called_once_with("\n")
		self.assertEqual([c.args[0] for c in typed.call_args_list], ["a", "b"])

	def test_typing_failure_is_a_normal_failure(self):
		with patch.object(backend, "type_unicode", side_effect=OSError("input failed")):
			self.assertFalse(
				ex.executeInstantAction({"type": "TextSnippets", "path": "abc", "typingDelay": 0})
			)

	def test_continue_after_exception_and_stop_on_error(self):
		for stop, expected in ((False, 2), (True, 1)):
			with (
				self.subTest(stop=stop),
				patch.object(ex, "executeInstantAction", side_effect=[ValueError("bad"), True]) as action,
			):
				self.assertFalse(ex.executeInstantItem({"actions": [{}, {}], "stopOnError": stop}))
				self.assertEqual(action.call_count, expected)

	def test_browser_failure_stops_following_action(self):
		with (
			patch.object(ex.webbrowser, "open", return_value=False),
			patch.object(ex, "setClipboardText") as copy,
		):
			self.assertFalse(
				ex.executeInstantItem(
					{
						"actions": [
							{"type": "Websites", "path": "https://example.invalid"},
							{"type": "TextSnippets", "path": "unexpected", "textAction": "copy"},
						]
					}
				)
			)
			copy.assert_not_called()

	def test_nonfinite_action_delays_never_execute(self):
		for value in ("inf", "nan", -1, 1e300):
			with self.subTest(value=value), patch.object(ex, "executeInstantAction") as action:
				self.assertFalse(ex.executeInstantItem({"actions": [{"delay": value}]}))
				action.assert_not_called()

	def test_nvda_waits_for_actual_script_not_just_dispatch(self):
		self.installScriptHost()
		events = []
		with (
			patch.object(
				commands, "_resolveBoundScript", return_value=lambda gesture: events.append("script")
			),
			patch.object(ex, "setClipboardText", side_effect=lambda text: events.append("copy") or True),
		):
			future = self.runner().submit(
				{
					"actions": [
						{"type": "NvdaCommands", "path": "module|Class|command"},
						{"type": "TextSnippets", "path": "after", "textAction": "copy"},
					]
				}
			)
			fn, args, kwargs = self.mainQueue.get(timeout=1)
			fn(*args, **kwargs)
			self.assertEqual(events, [])
			self.assertFalse(future.done())
			self.assertTrue(self.pump(future))
		self.assertEqual(events, ["script", "copy"])

	def test_nvda_exception_consumed_by_host_still_stops_item(self):
		self.installScriptHost()
		with (
			patch.object(
				commands, "_resolveBoundScript", return_value=Mock(side_effect=ValueError("script failed"))
			),
			patch.object(ex, "setClipboardText") as copied,
		):
			future = self.runner().submit(
				{
					"actions": [
						{"type": "NvdaCommands", "path": "module|Class|command"},
						{"type": "TextSnippets", "path": "after", "textAction": "copy"},
					]
				}
			)
			self.assertFalse(self.pump(future))
			copied.assert_not_called()

	def test_nvda_unavailable_stops_item(self):
		with (
			patch.object(commands, "_resolveBoundScript", return_value=None),
			patch.object(ex, "setClipboardText") as copied,
		):
			future = self.runner().submit(
				{
					"actions": [
						{"type": "NvdaCommands", "path": "module|Class|missing"},
						{"type": "TextSnippets", "path": "after", "textAction": "copy"},
					]
				}
			)
			self.assertFalse(self.pump(future))
			copied.assert_not_called()

	def test_emulated_script_send_does_not_finish_before_script_returns(self):
		self.installScriptHost()
		gesture = types.SimpleNamespace(send=Mock())
		completed = Mock()

		def script(gesture):
			gesture.send()
			completed.assert_not_called()
			raise ValueError("failure after sending")

		with (
			patch.object(commands.keyboardHandler.KeyboardInputGesture, "fromName", return_value=gesture),
			patch.object(
				commands.inputCore.manager, "emulateGesture", side_effect=lambda g: g.executeScript(script)
			),
		):
			commands.executeNvdaCommand("m|C|kb:a", onComplete=completed)
		completed.assert_called_once_with(False)

	def test_queue_limit_rejects_excess_work(self):
		started, release = threading.Event(), threading.Event()

		def execute(item, cancel):
			started.set()
			release.wait(2)
			return True

		with patch.object(ex, "executeInstantItem", side_effect=execute):
			runner = self.runner()
			first = runner.submit({})
			self.assertTrue(started.wait(1))
			for index in range(31):
				self.assertIsNotNone(runner.submit({}))
			self.assertIsNone(runner.submit({}))
			runner.shutdown()
			release.set()
			first.result(timeout=1)
		self.assertIn("Too many items", self.messages[-1])

	def test_shutdown_suppresses_already_dispatched_script(self):
		self.installScriptHost()
		script = Mock()
		with patch.object(commands, "_resolveBoundScript", return_value=script):
			runner = self.runner()
			future = runner.submit({"actions": [{"type": "NvdaCommands", "path": "m|C|s"}]})
			fn, args, kwargs = self.mainQueue.get(timeout=1)
			fn(*args, **kwargs)
			runner.shutdown()
			self.assertFalse(self.pump(future))
			self.runPending(self.scriptQueue)
			script.assert_not_called()

	def test_nvda_timeout_never_runs_late_callback(self):
		runner = self.runner()
		with patch.object(ex, "executeNvdaCommand") as command:
			future = runner._executor.submit(ex._executeNvdaAction, "m|C|s", None, 0.01)
			with self.assertRaises(TimeoutError):
				future.result(timeout=1)
			self.runPending(self.mainQueue)
			command.assert_not_called()

	def test_macro_items_are_serialized(self):
		firstCopy, releaseFirst = threading.Event(), threading.Event()
		clipboard = [None]
		pasted = []

		def copy(text):
			clipboard[0] = text
			if text == "A":
				firstCopy.set()
				if not releaseFirst.wait(1):
					raise TimeoutError()
			return True

		with (
			patch.object(ex, "setClipboardText", side_effect=copy),
			patch.object(keyboard, "send", side_effect=lambda key: pasted.append(clipboard[0])),
		):
			runner = self.runner()
			first = runner.submit({"actions": [{"type": "TextSnippets", "path": "A", "textAction": "paste"}]})
			self.assertTrue(firstCopy.wait(1))
			second = runner.submit(
				{"actions": [{"type": "TextSnippets", "path": "B", "textAction": "paste"}]}
			)
			self.assertEqual(clipboard[0], "A")
			releaseFirst.set()
			self.assertTrue(first.result(timeout=1))
			self.assertTrue(second.result(timeout=1))
		self.assertEqual(pasted, ["A", "B"])

	def test_shutdown_interrupts_delay_and_cancels_queued_work(self):
		started = threading.Event()
		originalWait = ex._wait

		def wait(delay, cancel=None):
			if delay == 60:
				started.set()
			return originalWait(delay, cancel)

		with patch.object(ex, "_wait", side_effect=wait), patch.object(ex, "executeInstantAction") as action:
			runner = self.runner()
			first = runner.submit({"actions": [{"delay": 60}]})
			self.assertTrue(started.wait(1))
			second = runner.submit({"actions": [{}]})
			runner.shutdown()
			self.assertFalse(first.result(timeout=1))
			self.assertTrue(second.cancelled())
			self.assertIsNone(runner.submit({"actions": [{}]}))
			action.assert_not_called()

	def test_queue_owns_snapshot_of_item(self):
		cancel = threading.Event()
		started = threading.Event()
		seen = []

		def execute(item, token):
			started.set()
			cancel.wait(1)
			seen.append(item["actions"][0]["path"])
			return True

		with patch.object(ex, "executeInstantItem", side_effect=execute):
			item = {"actions": [{"path": "original"}]}
			future = self.runner().submit(item)
			self.assertTrue(started.wait(1))
			item["actions"][0]["path"] = "modified"
			cancel.set()
			future.result(timeout=1)
		self.assertEqual(seen, ["original"])

	def test_secure_mode_get_script_is_safe(self):
		with patch.object(gv.appArgs, "secure", True):
			instance = plugin.GlobalPlugin()
			self.assertIsNone(instance.getScript(object()))
			instance.script_toggleInstantMode(None)
			instance.terminate()

	def test_win32_buffer_capacity_matches_allocation(self):
		tree = ast.parse(
			(ROOT / "addon/globalPlugins/core/keyboard/_winkeyboard.py").read_text(encoding="utf-8")
		)
		node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_event_names")
		calls = []
		env = {
			"keypad_keys": [],
			"official_virtual_keys": {},
			"keyboard_state": (ctypes.c_uint8 * 256)(),
			"unicode_buffer": ctypes.create_unicode_buffer(32),
			"name_buffer": ctypes.create_unicode_buffer(32),
			"ToUnicode": lambda *a: 0,
			"GetKeyNameText": lambda key, buf, size: calls.append((len(buf), size)) or 0,
			"user32": types.SimpleNamespace(MapVirtualKeyW=lambda *a: 0),
			"MAPVK_VK_TO_CHAR": 2,
		}
		exec(compile(ast.Module(body=[node], type_ignores=[]), "<wrapper-test>", "exec"), env)
		list(env["get_event_names"](1, 1, 0, ()))
		self.assertEqual(calls, [(32, 32)])

	def test_navigation_keys_are_sent_as_extended_keys(self):
		tree = ast.parse(
			(ROOT / "addon/globalPlugins/core/keyboard/_winkeyboard.py").read_text(encoding="utf-8")
		)
		wanted = {"EXTENDED_VKS", "_with_extended_flag", "_send_event"}
		nodes = [
			n
			for n in tree.body
			if getattr(n, "name", None) in wanted
			or (isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) in wanted)
		]
		sent = []
		env = {
			"KEYEVENTF_EXTENDEDKEY": 1,
			"scan_code_to_vk": {79: 0x23, 30: 0x41, 42: 0xA0},
			"user32": types.SimpleNamespace(keybd_event=lambda *args: sent.append(args)),
		}
		exec(compile(ast.Module(body=nodes, type_ignores=[]), "<extended-test>", "exec"), env)
		for code in (42, 79, 30):
			env["_send_event"](code, 0)
		env["_send_event"](79, 2)
		env["_send_event"](-0x25, 0)
		self.assertEqual(
			sent,
			[(0xA0, 42, 0, 0), (0x23, 79, 1, 0), (0x41, 30, 0, 0), (0x23, 79, 3, 0), (0x25, 0, 1, 0)],
		)

	@unittest.skipUnless(os.name == "nt", "Windows cmd quoting test")
	def test_batch_paths_and_arguments_on_windows(self):
		with tempfile.TemporaryDirectory(prefix="instant access ") as td:
			for filename in ("probe.cmd", "probe with spaces.cmd", "probe & other.cmd"):
				with self.subTest(filename=filename):
					batch = Path(td) / filename
					batch.write_text("@echo off\necho [%~1]\necho [%~2]\n")
					popen = subprocess.Popen
					outputs = []

					def capture(args, **kwargs):
						proc = popen(
							args,
							**kwargs,
							stdout=subprocess.PIPE,
							stderr=subprocess.PIPE,
							text=True,
							creationflags=subprocess.CREATE_NO_WINDOW,
						)
						out, err = proc.communicate(timeout=5)
						outputs.append((proc.returncode, out.strip(), err.strip()))
						return proc

					with patch.object(ex.subprocess, "Popen", side_effect=capture):
						self.assertTrue(
							ex.executeInstantAction(
								{"type": "Programs", "path": str(batch), "arguments": 'alpha "beta gamma"'}
							)
						)
					self.assertEqual(outputs, [(0, "[alpha]\n[beta gamma]", "")])
