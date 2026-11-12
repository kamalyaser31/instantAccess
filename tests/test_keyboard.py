import importlib.util
import sys
import types
import unittest
from unittest.mock import Mock, patch

from nvda_stubs import ROOT, dialogs, ex
from auditcore import gestures


class KeyboardTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		path = ROOT / "addon/globalPlugins/core/keyboard"
		spec = importlib.util.spec_from_file_location(
			"keyboard_under_test", path / "__init__.py", submodule_search_locations=[str(path)]
		)
		cls.keyboard = importlib.util.module_from_spec(spec)
		sys.modules[spec.name] = cls.keyboard
		with patch("ctypes.WinDLL", return_value=Mock(), create=True):
			spec.loader.exec_module(cls.keyboard)
		cls.backend = cls.keyboard._os_keyboard

	@classmethod
	def tearDownClass(cls):
		for name in list(sys.modules):
			if name == "keyboard_under_test" or name.startswith("keyboard_under_test."):
				del sys.modules[name]

	def setUp(self):
		self.sent = []
		# These ambiguous Windows names reproduced the original wrong-key selection.
		entries = {
			"right ctrl": [(0, (0xE11D, 0x13, 0, ()))],
			"right alt": [(0, (0x38, 0xA4, 1, ()))],
			"a": [(0, (0x1E, 0x41, 0, ()))],
			"v": [(0, (0x2F, 0x56, 0, ()))],
			"1": [(0, (0x02, 0x31, 0, ()))],
			"/": [(0, (0x35, 0xBF, 0, ()))],
			"f2": [(0, (0x3C, 0x71, 0, ()))],
			",": [(0, (0x33, 0xBC, 0, ()))],
			"+": [(0, (0x0D, 0xBB, 0, ()))],
		}
		for patcher in (
			patch.object(self.backend, "_setup_name_tables"),
			patch.dict(self.backend.from_name, entries, clear=True),
			patch.dict(self.backend.scan_code_to_vk, {0x1E: 0x99}, clear=True),
			patch.object(
				self.backend.user32, "keybd_event", side_effect=lambda *args: self.sent.append(args)
			),
			patch.object(ex, "keyboard", self.keyboard),
		):
			patcher.start()
			self.addCleanup(patcher.stop)

	def assertKey(self, name, vk, scan, extended):
		self.sent.clear()
		self.assertTrue(ex.isValidKeystroke(name))
		self.keyboard.send(name)
		self.assertEqual(self.sent, [(vk, scan, extended, 0), (vk, scan, extended | 2, 0)])

	def test_special_keys_keep_their_identity_on_press_and_release(self):
		for name, vk, scan, extended in (
			("home", 0x24, 0x47, 1),
			("end", 0x23, 0x4F, 1),
			("up", 0x26, 0x48, 1),
			("down", 0x28, 0x50, 1),
			("left", 0x25, 0x4B, 1),
			("right", 0x27, 0x4D, 1),
			("pageup", 0x21, 0x49, 1),
			("pagedown", 0x22, 0x51, 1),
			("insert", 0x2D, 0x52, 1),
			("delete", 0x2E, 0x53, 1),
			("left ctrl", 0xA2, 0x1D, 0),
			("right ctrl", 0xA3, 0x1D, 1),
			("left alt", 0xA4, 0x38, 0),
			("right alt", 0xA5, 0x38, 1),
			("right menu", 0xA5, 0x38, 1),
			("left shift", 0xA0, 0x2A, 0),
			("right shift", 0xA1, 0x36, 0),
			("left windows", 0x5B, 0x5B, 1),
			("right windows", 0x5C, 0x5C, 1),
			("applications", 0x5D, 0x5D, 1),
			("print screen", 0x2C, 0x37, 1),
			("pause", 0x13, 0x45, 0),
			("num lock", 0x90, 0x45, 1),
			("enter", 0x0D, 0x1C, 0),
			("numpadEnter", 0x0D, 0x1C, 1),
			("numpadDivide", 0x6F, 0x35, 1),
			("numpadMultiply", 0x6A, 0x37, 0),
			("numpadMinus", 0x6D, 0x4A, 0),
			("numpadPlus", 0x6B, 0x4E, 0),
			("numpadDecimal", 0x6E, 0x53, 0),
			("numpadHome", 0x24, 0x47, 0),
			("numpadEnd", 0x23, 0x4F, 0),
			("numpadUp", 0x26, 0x48, 0),
			("numpadDown", 0x28, 0x50, 0),
			("numpadLeft", 0x25, 0x4B, 0),
			("numpadRight", 0x27, 0x4D, 0),
			("numpadPageUp", 0x21, 0x49, 0),
			("numpadPageDown", 0x22, 0x51, 0),
			("numpadInsert", 0x2D, 0x52, 0),
			("numpadDelete", 0x2E, 0x53, 0),
			("numpadClear", 0x0C, 0x4C, 0),
			("a", 0x41, 0x1E, 0),
			("1", 0x31, 0x02, 0),
			("/", 0xBF, 0x35, 0),
		):
			with self.subTest(name=name):
				self.assertKey(name, vk, scan, extended)

	def test_keypad_digit_aliases_do_not_become_top_row_digits(self):
		for digit, scan in enumerate((0x52, 0x4F, 0x50, 0x51, 0x4B, 0x4C, 0x4D, 0x47, 0x48, 0x49)):
			for name in (f"numpad{digit}", f"num {digit}"):
				with self.subTest(name=name):
					self.assertKey(name, 0x60 + digit, scan, 0)
		for name, vk, scan, extended in (
			("num enter", 0x0D, 0x1C, 1),
			("num divide", 0x6F, 0x35, 1),
			("num multiply", 0x6A, 0x37, 0),
			("num plus", 0x6B, 0x4E, 0),
			("num minus", 0x6D, 0x4A, 0),
		):
			with self.subTest(name=name):
				self.assertKey(name, vk, scan, extended)

	def test_recorded_keypad_names_pass_validation_and_execute(self):
		wx = Mock(WXK_F1=300, WXK_F24=323, WXK_NUMPAD0=400, WXK_NUMPAD9=409)
		cases = (
			(401, "numLockNumpad1", "numpad1", 0x61, 0x4F, 0),
			(410, "numpadEnter", "numpadenter", 0x0D, 0x1C, 1),
			(411, "numpadDivide", "numpaddivide", 0x6F, 0x35, 1),
			(412, "numpad7", "numpadhome", 0x24, 0x47, 0),
			(413, "numpadDecimal", "numpaddecimal", 0x6E, 0x53, 0),
			(414, "numpadPlus", "numpadplus", 0x6B, 0x4E, 0),
			(415, "numpadMinus", "numpadminus", 0x6D, 0x4A, 0),
			(416, "numpadMultiply", "numpadmultiply", 0x6A, 0x37, 0),
			(417, "numpadDivide", "numpaddivide", 0x6F, 0x35, 1),
		)
		wx.WXK_NUMPAD_ENTER = 410
		wx.WXK_DIVIDE = 411
		wx.WXK_NUMPAD_HOME = 412
		wx.WXK_NUMPAD_DECIMAL = 413
		wx.WXK_NUMPAD_ADD = 414
		wx.WXK_NUMPAD_SUBTRACT = 415
		wx.WXK_NUMPAD_MULTIPLY = 416
		wx.WXK_NUMPAD_DIVIDE = 417
		with patch.object(gestures, "wx", wx):
			for code, shortcut, recorded, vk, scan, extended in cases:
				with self.subTest(recorded=recorded):
					event = Mock()
					event.GetKeyCode.return_value = code
					for name in ("ControlDown", "AltDown", "ShiftDown", "MetaDown"):
						getattr(event, name).return_value = False
					self.assertEqual(gestures.buildGestureNameFromEvent(event), shortcut)
					line = gestures.gestureToKeystroke(shortcut)
					self.assertEqual(line, recorded)
					dialog = types.SimpleNamespace(lines=[])
					self.assertEqual(dialogs.KeystrokeRecordDialog._record(dialog, line), line)
					self.assertEqual(dialog.lines, [line])
					self.sent.clear()
					self.assertTrue(ex._sendKeystrokeSequence(line, 0))
					self.assertEqual(self.sent, [(vk, scan, extended, 0), (vk, scan, extended | 2, 0)])

	def test_combinations_release_in_reverse_order_and_keep_extended_flags(self):
		self.keyboard.send("right ctrl+shift+home, ctrl+v")
		self.assertEqual(
			self.sent,
			[
				(0xA3, 0x1D, 1, 0),
				(0xA0, 0x2A, 0, 0),
				(0x24, 0x47, 1, 0),
				(0x24, 0x47, 3, 0),
				(0xA0, 0x2A, 2, 0),
				(0xA3, 0x1D, 3, 0),
				(0xA2, 0x1D, 0, 0),
				(0x56, 0x2F, 0, 0),
				(0x56, 0x2F, 2, 0),
				(0xA2, 0x1D, 2, 0),
			],
		)

	def test_failure_releases_the_same_right_modifier(self):
		def send(vk, scan, flags, extra):
			if vk == 0x41:
				raise OSError("input failed")
			self.sent.append((vk, scan, flags, extra))

		with patch.object(self.backend.user32, "keybd_event", side_effect=send):
			with self.assertRaises(OSError):
				self.keyboard.send("right ctrl+a")
		self.assertEqual(self.sent, [(0xA3, 0x1D, 1, 0), (0xA3, 0x1D, 3, 0)])

	def test_dynamic_mapping_keeps_vk_and_e0_prefix_without_reverse_lookup(self):
		with patch.dict(self.backend.from_name, {"browser back": [(0, (0xE06A, 0xA6, 0, ()))]}):
			self.assertKey("browser back", 0xA6, 0x6A, 1)

	def test_unknown_names_are_rejected(self):
		self.assertFalse(ex.isValidKeystroke("not a key"))
		self.assertEqual(self.sent, [])

	def test_existing_sequence_syntax_and_raw_codes_still_work(self):
		self.assertTrue(ex._sendKeystrokeSequence("# comment\nf2\nshift+home 2\nctrl+comma\nctrl+plus", 0))
		self.assertEqual(
			[e[0] for e in self.sent if not e[2] & 2], [0x71, 0xA0, 0x24, 0xA0, 0x24, 0xA2, 0xBC, 0xA2, 0xBB]
		)
		self.sent.clear()
		self.keyboard.send(-0x25)
		self.assertEqual(self.sent, [(0x25, 0, 1, 0), (0x25, 0, 3, 0)])

	def test_repetition_and_cancellation_still_use_the_same_sender(self):
		cancel = Mock()
		cancel.is_set.side_effect = [False, True]
		cancel.wait.return_value = False
		self.assertFalse(ex._sendKeystrokeSequence("right ctrl 3", 0, cancel))
		self.assertEqual(self.sent, [(0xA3, 0x1D, 1, 0), (0xA3, 0x1D, 3, 0)])
