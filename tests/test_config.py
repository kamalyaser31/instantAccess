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
			manager.saveItem(None, "new", "kb:n", [{"type": "Websites", "path": "https://example.invalid"}])
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

	def test_no_disk_writes_when_nvda_forbids_them(self):
		with patch.object(io.NVDAState, "shouldWriteToDisk", return_value=False):
			cm.ConfigManager(self.path)
			self.assertFalse(Path(self.path).exists())
			with self.assertRaises(io.DiskWriteDisabledError):
				io.saveConfig(self.path, self.config)
		self.assertFalse(Path(self.path).exists())

	def test_recovery_without_disk_writes_uses_backup_in_memory(self):
		self.damaged()
		self.prompt.return_value = wx.YES
		with patch.object(io.NVDAState, "shouldWriteToDisk", return_value=False):
			self.assertEqual(io.loadConfigSafe(self.path)["items"][0]["name"], "original")
		self.assertEqual(Path(self.path).read_text(), "{broken")

	def test_config_is_read_once_and_refreshed_after_save(self):
		self.write(self.config)
		manager = cm.ConfigManager(self.path)
		with patch.object(cm, "loadConfigSafe", wraps=io.loadConfigSafe) as load:
			manager.getItems()
			manager.getSettings()
			manager.getItems()
			self.assertEqual(load.call_count, 1)
			manager.saveItem(None, "second", "kb:s", [{"type": "Websites", "path": "https://example.invalid"}])
			self.assertEqual([item["name"] for item in manager.getItems()], ["original", "second"])
			self.assertEqual(load.call_count, 2)

	def test_declined_recovery_is_asked_once(self):
		self.damaged()
		manager = cm.ConfigManager(self.path)
		manager.getItems()
		manager.getItems()
		self.assertEqual(self.prompt.call_count, 1)

	def test_zero_delays_survive_roundtrip(self):
		manager = cm.ConfigManager(self.path)
		manager.saveItem(
			None,
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

	def test_move_item_swaps_neighbours_and_stops_at_the_ends(self):
		def item(name):
			return {
				"name": name,
				"gesture": "kb:" + name,
				"actions": [{"type": "Websites", "data": {"url": "https://example.invalid"}}],
			}

		self.write({"version": 3, "items": [item("a"), item("b"), item("c")]})
		manager = cm.ConfigManager(self.path)
		self.assertTrue(manager.moveItem("b", -1))
		self.assertFalse(manager.moveItem("b", -1))
		self.assertFalse(manager.moveItem("c", 1))
		self.assertFalse(manager.moveItem("missing", 1))
		self.assertEqual([entry["name"] for entry in manager.getItems()], ["b", "a", "c"])
		self.assertEqual([entry["name"] for entry in cm.ConfigManager(self.path).getItems()], ["b", "a", "c"])

	def test_run_as_admin_is_stored_only_when_ticked(self):
		manager = cm.ConfigManager(self.path)
		manager.saveItem("", "admin", "kb:x", [{"type": "Programs", "path": "cmd", "runAsAdmin": True}])
		manager.saveItem("", "plain", "kb:y", [{"type": "Programs", "path": "cmd"}])
		items = {entry["name"]: entry for entry in cm.ConfigManager(self.path).getItems()}
		self.assertTrue(items["admin"]["actions"][0]["runAsAdmin"])
		self.assertFalse(items["plain"]["actions"][0]["runAsAdmin"])
		stored = json.loads(Path(self.path).read_text(encoding="utf-8"))["items"]
		self.assertNotIn("runAsAdmin", [i for i in stored if i["name"] == "plain"][0]["actions"][0]["data"])

	def test_enabled_and_announce_name_are_stored_only_when_changed(self):
		manager = cm.ConfigManager(self.path)
		action = {"type": "Websites", "path": "https://example.invalid"}
		manager.saveItem("", "off", "kb:x", [action], enabled=False, announceName="off")
		manager.saveItem("", "plain", "kb:y", [action])
		items = {entry["name"]: entry for entry in cm.ConfigManager(self.path).getItems()}
		self.assertEqual((items["off"]["enabled"], items["off"]["announceName"]), (False, "off"))
		self.assertEqual((items["plain"]["enabled"], items["plain"]["announceName"]), (True, "default"))
		stored = json.loads(Path(self.path).read_text(encoding="utf-8"))["items"]
		plain = [item for item in stored if item["name"] == "plain"][0]
		self.assertNotIn("enabled", plain)
		self.assertNotIn("announceName", plain)

	def test_a_disabled_item_still_conflicts_on_its_shortcut(self):
		manager = cm.ConfigManager(self.path)
		action = {"type": "Websites", "path": "https://example.invalid"}
		manager.saveItem("", "off", "kb:x", [action], enabled=False)
		self.assertEqual(manager.findGestureConflict("kb:x")["name"], "off")

	def test_invalid_enabled_and_announce_values_are_refused(self):
		for field, value in (("enabled", "no"), ("announceName", "maybe")):
			with self.subTest(field=field):
				config = copy.deepcopy(self.config)
				config["items"][0][field] = value
				with self.assertRaises(ValueError):
					io._validateConfig(config)

	def test_several_apps_share_a_conflict_check(self):
		manager = cm.ConfigManager(self.path)
		action = {"type": "Websites", "path": "https://example.invalid"}
		manager.saveItem("", "editors", "kb:x", [action], appName="Notepad, winword")
		self.assertEqual(manager.findGestureConflict("kb:x", "excel, WINWORD")["name"], "editors")
		self.assertIsNone(manager.findGestureConflict("kb:x", "excel"))
		self.assertIsNone(manager.findGestureConflict("kb:x", ""))
		self.assertEqual(cm.ConfigManager(self.path).getItems()[-1]["appName"], "notepad, winword")
		with self.assertRaises(ValueError):
			manager.saveItem("", "other", "kb:x", [action], appName="winword")

	def test_merge_adds_new_items_and_keeps_settings(self):
		def item(name, gesture, appName=""):
			entry = {
				"name": name,
				"gesture": gesture,
				"actions": [{"type": "Websites", "data": {"url": "https://example.invalid"}}],
			}
			if appName:
				entry["appName"] = appName
			return entry

		self.write({"version": 3, "settings": {"verbosity": "advanced"}, "items": [item("a", "kb:a", "notepad")]})
		manager = cm.ConfigManager(self.path)
		imported = {
			"settings": {"verbosity": "beginner"},
			"items": [
				item("a", "kb:n"),
				item("clash", "kb:a", "notepad, excel"),
				item("elsewhere", "kb:a", "excel"),
				item("new", "kb:b"),
			],
		}
		self.assertEqual(manager.mergeItems(imported), (2, 2))
		self.assertEqual([entry["name"] for entry in manager.getItems()], ["a", "elsewhere", "new"])
		self.assertEqual(manager.getVerbosityLevel(), "advanced")

	def test_edit_keeps_item_position(self):
		def item(name):
			return {
				"name": name,
				"gesture": "kb:" + name,
				"actions": [{"type": "Websites", "data": {"url": "https://example.invalid"}}],
			}

		self.write({"version": 3, "items": [item("a"), item("b"), item("c")]})
		manager = cm.ConfigManager(self.path)
		action = {"type": "Websites", "path": "https://example.invalid"}
		manager.saveItem("b", "renamed", "kb:b", [action])
		self.assertEqual([entry["name"] for entry in manager.getItems()], ["a", "renamed", "c"])
