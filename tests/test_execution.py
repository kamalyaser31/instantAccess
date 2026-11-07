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

		def execute(item, cancel, context=None):
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

		def execute(item, token, context=None):
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

	def test_is_busy_tracks_execution(self):
		runner = self.runner()
		self.assertFalse(runner.isBusy())
		started = threading.Event()
		proceed = threading.Event()

		def blockingAction(*a, **kw):
			started.set()
			proceed.wait(1)
			return True

		with patch.object(ex, "executeInstantItem", side_effect=blockingAction):
			future = runner.submit({"actions": [{"type": "TextSnippets", "path": "test"}]})
			self.assertTrue(started.wait(1))
			self.assertTrue(runner.isBusy())
			proceed.set()
			future.result(timeout=1)
			self.assertFalse(runner.isBusy())

	def test_cancel_current_stops_running_task_and_drops_queued_work(self):
		runner = self.runner()
		started = threading.Event()

		def longWait(delay, cancelEvent=None):
			started.set()
			if cancelEvent:
				cancelEvent.wait(5)
			return False

		with patch.object(ex, "_wait", side_effect=longWait):
			first = runner.submit({"actions": [{"type": "TextSnippets", "path": "long"}]})
			self.assertTrue(started.wait(1))
			self.assertTrue(runner.isBusy())

			second = runner.submit({"actions": [{"type": "TextSnippets", "path": "queued"}]})
			self.assertTrue(runner.cancelCurrent())
			self.assertFalse(first.result(timeout=1))
			self.assertTrue(second.cancelled())
			self.assertFalse(runner.isBusy())

	def test_nvda_e_cancels_running_task_without_opening_layer(self):
		instance = plugin.GlobalPlugin.__new__(plugin.GlobalPlugin)
		instance._enabled = True
		instance.instantMode = False
		instance.verbosityLevel = "beginner"
		instance.queueTone = Mock()
		instance.activateInstantMode = Mock()
		instance.deactivateInstantMode = Mock()
		instance.executionQueue = Mock()
		instance.executionQueue.isBusy.return_value = True

		# Beginner verbosity announces speech
		with patch("ui.message") as msg:
			instance.script_toggleInstantMode(None)
			instance.executionQueue.cancelCurrent.assert_called_once()
			msg.assert_called_with("Cancelled")
			instance.activateInstantMode.assert_not_called()
			instance.deactivateInstantMode.assert_not_called()

		# Advanced verbosity emits tone
		instance.verbosityLevel = "advanced"
		instance.script_toggleInstantMode(None)
		instance.queueTone.assert_called_with(250, 50)

	def test_placeholder_substitution_and_escaping(self):
		import auditcore.placeholders as ph

		context = {
			"selection": "sel text",
			"file": r"C:\path\file.txt",
			"folder": r"C:\path",
			"fileList": [r"C:\path\file.txt"],
		}
		# Raw snippet substitution
		text = "Date: {date}, Clip: {clipboard}, Sel: {selection}, Esc: {{date}}, Unknown: {foo}"
		res = ph.substitutePlaceholders(text, context=context, getClipboardFn=lambda: "clip text")
		self.assertIn("Clip: clip text", res)
		self.assertIn("Sel: sel text", res)
		self.assertIn("Esc: {date}", res)
		self.assertIn("Unknown: {foo}", res)

		# URL encoding
		url = "https://www.google.com/search?q={clipboard}"
		resUrl = ph.substitutePlaceholders(
			url, context=context, getClipboardFn=lambda: "hello world & more", encoding="url"
		)
		self.assertEqual(resUrl, "https://www.google.com/search?q=hello%20world%20%26%20more")

		# Arguments quoting
		args = "--path {file}"
		resArgs = ph.substitutePlaceholders(
			args, context=context, getClipboardFn=lambda: "", encoding="argument"
		)
		self.assertEqual(resArgs, r'--path "C:\path\file.txt"')

	def test_multi_file_placeholder_in_arguments(self):
		import auditcore.placeholders as ph

		context = {
			"file": r'"C:\path\one.txt" "C:\path\two.txt"',
			"fileList": [r"C:\path\one.txt", r"C:\path\two.txt"],
		}
		args = "--files {file}"
		res = ph.substitutePlaceholders(args, context=context, encoding="argument")
		self.assertEqual(res, r'--files "C:\path\one.txt" "C:\path\two.txt"')

	def test_batch_file_arguments_refuse_variables(self):
		import auditcore.placeholders as ph

		for var in ("{clipboard}", "{file}", "{folder}", "{selection}"):
			with self.subTest(var=var):
				item = {
					"actions": [
						{"type": "Programs", "path": "script.bat", "arguments": f"--opt {var}"}
					]
				}
				valid, msg = ph.validateItemContext(item)
				self.assertFalse(valid)
				self.assertIn("batch file arguments", msg)

	def test_empty_context_variables_stop_item_execution(self):
		import auditcore.placeholders as ph

		for var, expectedError in (
			("{selection}", "No text is selected."),
			("{file}", "No file is selected in File Explorer."),
			("{folder}", "No folder is open in File Explorer."),
		):
			with self.subTest(var=var):
				item = {
					"actions": [
						{"type": "TextSnippets", "path": f"Insert: {var}"}
					]
				}
				valid, msg = ph.validateItemContext(item, context={})
				self.assertFalse(valid)
				self.assertEqual(msg, expectedError)

	def test_execution_stops_before_running_when_context_variable_empty(self):
		item = {
			"actions": [
				{"type": "TextSnippets", "path": "Selected: {selection}"}
			]
		}
		runner = self.runner()
		with (
			patch.object(ex, "executeInstantAction") as actionMock,
			patch.object(ex, "_captureContextOnMainThread", return_value={"selection": ""}),
		):
			future = runner.submit(item)
			self.assertFalse(future.result(timeout=1))
			actionMock.assert_not_called()
		self.assertIn("No text is selected.", self.messages[-1])

	def test_context_is_read_only_for_items_that_use_it(self):
		runner = self.runner()
		with (
			patch.object(ex, "executeInstantAction", return_value=True) as actionMock,
			patch.object(ex, "_captureContextOnMainThread", return_value={"selection": "S"}) as capture,
		):
			runner.submit({"actions": [{"type": "TextSnippets", "path": "plain {date}"}]}).result(timeout=1)
			capture.assert_not_called()
			runner.submit({"actions": [{"type": "TextSnippets", "path": "{selection}"}]}).result(timeout=1)
			capture.assert_called_once()
		self.assertEqual(actionMock.call_args.kwargs["context"], {"selection": "S"})

	def test_context_snapshot_waits_for_the_main_thread_and_stops_on_cancel(self):
		cancelEvent = threading.Event()
		cancelEvent.set()
		with patch.object(ex.wx, "CallAfter", side_effect=lambda fn: fn()):
			with patch.object(ex, "captureContextSnapshot", return_value={"file": "F"}):
				self.assertEqual(ex._captureContextOnMainThread(None), {"file": "F"})
		with patch.object(ex.wx, "CallAfter"):
			self.assertEqual(ex._captureContextOnMainThread(cancelEvent), {})

	def test_a_batch_file_found_on_the_path_also_refuses_variables(self):
		import auditcore.placeholders as ph

		item = {"actions": [{"type": "Programs", "path": "npm", "arguments": "{clipboard}"}]}
		with (
			patch.object(ph.os.path, "exists", return_value=False),
			patch.object(ph.shutil, "which", return_value=r"C:\tools\npm.cmd"),
		):
			self.assertFalse(ph.validateItemContext(item)[0])
		with (
			patch.object(ph.os.path, "exists", return_value=False),
			patch.object(ph.shutil, "which", return_value=r"C:\tools\npm.exe"),
		):
			self.assertTrue(ph.validateItemContext(item)[0])

	def test_a_drive_root_keeps_its_closing_quote(self):
		import auditcore.placeholders as ph

		res = ph.substitutePlaceholders("{folder}", context={"folder": "C:\\"}, encoding="argument")
		self.assertEqual(res, '"C:\\\\"')
		self.assertEqual(ex.subprocess.list2cmdline(["C:\\"]), "C:\\")

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

	def _paste(self, previousText, sendError=None, cancelEvent=None):
		clipboard = []
		with (
			patch.object(ex.api, "getClipData", return_value=previousText, create=True),
			patch.object(ex.api, "copyToClip", side_effect=lambda text, notify: clipboard.append(text) or True),
			patch.object(ex.keyboard, "send", side_effect=sendError),
			patch.object(ex, "PASTE_SETTLE_SECONDS", 0),
		):
			result = ex.executeInstantAction(
				{"type": "TextSnippets", "path": "snippet", "textAction": "paste"}, cancelEvent
			)
		return result, clipboard

	def test_paste_restores_the_previous_clipboard_text(self):
		self.assertEqual(self._paste("old"), (True, ["snippet", "old"]))

	def test_paste_leaves_the_snippet_when_the_clipboard_had_no_text(self):
		self.assertEqual(self._paste(""), (True, ["snippet"]))

	def test_paste_failure_still_restores_the_clipboard(self):
		self.assertEqual(self._paste("old", sendError=OSError("blocked")), (False, ["snippet", "old"]))

	def test_run_as_admin_uses_runas_and_a_declined_prompt_is_not_an_error(self):
		declined = OSError("declined")
		declined.winerror = ex.ERROR_CANCELLED
		failed = OSError("failed")
		action = {"type": "Programs", "path": "tool.exe", "arguments": "-x", "runAsAdmin": True}
		with (
			patch.object(ex.os.path, "exists", return_value=True),
			patch.object(ex, "queueMessage") as message,
			patch.object(ex.subprocess, "Popen") as popen,
			patch.object(ex.os, "startfile", create=True) as startfile,
		):
			self.assertTrue(ex.executeInstantAction(action))
			startfile.assert_called_once_with("tool.exe", "runas", "-x", None)
			startfile.side_effect = declined
			self.assertTrue(ex.executeInstantAction(action))
			startfile.side_effect = failed
			self.assertFalse(ex.executeInstantAction(action))
		popen.assert_not_called()
		self.assertEqual(message.call_count, 2)

	def test_paste_waits_after_cancel_before_restoring(self):
		cancelEvent = threading.Event()
		events = []
		with (
			patch.object(ex.api, "getClipData", return_value="old", create=True),
			patch.object(ex.api, "copyToClip", side_effect=lambda text, notify: events.append(text) or True),
			patch.object(ex.keyboard, "send", side_effect=lambda keys: cancelEvent.set()),
			patch.object(ex, "_wait", side_effect=lambda delay, event=None: events.append(("wait", event))),
		):
			ex.executeInstantAction({"type": "TextSnippets", "path": "s", "textAction": "paste"}, cancelEvent)
		self.assertEqual(events, ["s", ("wait", None), "old"])

	def test_failed_clipboard_restore_is_spoken(self):
		results = iter([True, False])
		with (
			patch.object(ex.api, "getClipData", return_value="old", create=True),
			patch.object(ex.api, "copyToClip", side_effect=lambda text, notify: next(results)),
			patch.object(ex.keyboard, "send"),
			patch.object(ex, "PASTE_SETTLE_SECONDS", 0),
			patch.object(ex, "queueMessage") as message,
		):
			ex.executeInstantAction({"type": "TextSnippets", "path": "s", "textAction": "paste"})
		message.assert_called_once()

	def test_a_keystroke_that_would_read_as_a_comment_is_invalid(self):
		with patch.object(ex.keyboard, "parse_hotkey"):
			self.assertFalse(ex.isValidKeystroke("#"))
			self.assertTrue(ex.isValidKeystroke("control+#"))

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
