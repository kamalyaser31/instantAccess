import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nvda_stubs import io, cm, gui, wx


class ConfigTests(unittest.TestCase):
	def test_duplicate_name_remains_unique_after_999_copies(self):
		names = {"name (copy)"} | {f"name (copy {index})" for index in range(2, 1000)}
		manager = cm.ConfigManager.__new__(cm.ConfigManager)
		with patch.object(manager, "getAllNames", return_value=names):
			self.assertEqual(manager.getUniqueItemName("name"), "name (copy 1000)")

	def setUp(self):
		self.temp = tempfile.TemporaryDirectory()
		self.addCleanup(self.temp.cleanup)
		self.path = str(Path(self.temp.name) / "config.json")
		self.backup = Path(self.path + ".bak")
		self.config = {
			"version": 3,
			"items": [
				{
					"name": "original",
					"gesture": "kb:a",
					"actions": [
						{"type": "Websites", "data": {"url": "https://example.invalid"}},
					],
				}
			],
		}
		self.prompt = patch.object(gui, "messageBox", return_value=wx.NO).start()
		self.addCleanup(patch.stopall)

	def write(self, data):
		Path(self.path).write_text(json.dumps(data), encoding="utf-8")

	def damaged(self):
		Path(self.path).write_text("{broken", encoding="utf-8")
		self.backup.write_text(json.dumps(self.config), encoding="utf-8")

	def test_declined_recovery_preserves_both_files(self):
		self.damaged()
		before = self.backup.read_bytes()
		self.assertEqual(io.loadConfigSafe(self.path)["items"], [])
		self.assertEqual(Path(self.path).read_text(), "{broken")
		self.assertEqual(self.backup.read_bytes(), before)

	def test_accepted_recovery_preserves_backup(self):
		self.damaged()
		before = self.backup.read_bytes()
		self.prompt.return_value = wx.YES
		self.assertEqual(io.loadConfigSafe(self.path)["items"][0]["name"], "original")
		self.assertEqual(self.backup.read_bytes(), before)

	def test_missing_primary_recovers_before_creation(self):
		self.backup.write_text(json.dumps(self.config), encoding="utf-8")
		manager = cm.ConfigManager(self.path)
		self.assertFalse(Path(self.path).exists())
		self.prompt.return_value = wx.YES
		self.assertEqual(manager.getItems()[0]["name"], "original")

	def test_failed_recovery_write_does_not_destroy_backup(self):
		self.damaged()
		before = self.backup.read_bytes()
		self.prompt.return_value = wx.YES
		with patch.object(io.os, "replace", side_effect=OSError("disk error")):
			io.loadConfigSafe(self.path)
		self.assertEqual(Path(self.path).read_text(), "{broken")
		self.assertEqual(self.backup.read_bytes(), before)
		self.assertEqual(len(list(Path(self.temp.name).iterdir())), 2)

	def test_update_cannot_save_empty_recovery_fallback(self):
		self.damaged()
		manager = cm.ConfigManager(self.path)
		self.assertEqual(manager.getItems(), [])
		with self.assertRaises(ValueError):
			manager.addItem("new", "kb:n", [{"type": "Websites", "path": "https://example.invalid"}])
		self.assertEqual(Path(self.path).read_text(), "{broken")

	def test_normal_save_rotates_previous_valid_config(self):
		self.write(self.config)
		changed = copy.deepcopy(self.config)
		changed["items"][0]["name"] = "updated"
		io.saveConfig(self.path, changed)
		self.assertEqual(io.loadConfigFromPathStrict(str(self.backup))["items"][0]["name"], "original")
		self.assertEqual(io.loadConfigFromPathStrict(self.path)["items"][0]["name"], "updated")

	def test_strict_import_rejects_unknown_schema(self):
		for data in ({}, {"unrelated": 1}, {"items": {}}, {"version": 99, "items": []}):
			with self.subTest(data=data):
				self.write(data)
				with self.assertRaises(ValueError):
					io.loadConfigFromPathStrict(self.path)

	def test_invalid_items_are_not_silently_discarded(self):
		for field, value in (("name", 123), ("gesture", None), ("actions", []), ("interval", "inf")):
			with self.subTest(field=field):
				data = copy.deepcopy(self.config)
				data["items"][0][field] = value
				with self.assertRaises(ValueError):
					io.saveConfig(self.path, data)
				self.assertFalse(Path(self.path).exists())

	def test_duplicate_names_rejected(self):
		self.config["items"].append(copy.deepcopy(self.config["items"][0]))
		with self.assertRaises(ValueError):
			io.saveConfig(self.path, self.config)

	def test_zero_delays_survive_roundtrip(self):
		manager = cm.ConfigManager(self.path)
		manager.addItem(
			"zero",
			"kb:z",
			[
				{"type": "TextSnippets", "path": "hello", "typingDelay": 0},
				{"type": "Keystrokes", "path": "down", "pressDelay": 0},
			],
		)
		actions = manager.getItems()[0]["actions"]
		self.assertEqual(actions[0]["typingDelay"], 0)
		self.assertEqual(actions[1]["pressDelay"], 0)

	def test_older_v3_without_stop_on_error_is_supported(self):
		self.write(self.config)
		self.assertTrue(io.loadConfigFromPathStrict(self.path)["items"][0]["stopOnError"])

	def test_nonfinite_values_rejected(self):
		for value in ("inf", "nan", "-inf", 1e300, -1, True):
			with self.subTest(value=value), self.assertRaises((ValueError, OverflowError)):
				io.parseDelay(value)
