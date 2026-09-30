import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

from nvda_stubs import cm, io, plugin
import auditcore.browse as browse
import globalPluginHandler
import ui


def item(name, gesture, appName=""):
	return {"name": name, "gestures": [gesture], "appName": appName, "actions": []}


def storedItem(name, gesture, appName=""):
	data = {
		"name": name,
		"gesture": gesture,
		"actions": [{"type": "Websites", "data": {"url": "https://example.invalid"}}],
	}
	if appName:
		data["appName"] = appName
	return data


class BrowseHelperTests(unittest.TestCase):
	def test_usable_items_follow_current_app(self):
		globalG = item("Global G", "kb:g")
		notepadG = item("Notepad G", "kb:g", "notepad")
		wordOnly = item("Word only", "kb:w", "winword")
		items = [globalG, notepadG, wordOnly]
		self.assertEqual(browse.getUsableItems(items, "notepad"), [notepadG])
		self.assertEqual(browse.getUsableItems(items, "explorer"), [globalG])

	def test_sort_orders(self):
		items = [item("beta", "kb:a"), item("Alpha", "kb:shift+c"), item("gamma", "kb:b")]
		self.assertEqual([i["name"] for i in browse.sortItems(items, "list")], ["beta", "Alpha", "gamma"])
		self.assertEqual([i["name"] for i in browse.sortItems(items, "name")], ["Alpha", "beta", "gamma"])
		self.assertEqual([i["name"] for i in browse.sortItems(items, "key")], ["beta", "gamma", "Alpha"])

	def test_announcement_formats(self):
		gmail = item("Open Gmail", "kb:g")
		self.assertEqual(browse.formatItem(gmail, "nameKey"), "Open Gmail, g")
		self.assertEqual(browse.formatItem(gmail, "keyName"), "g, Open Gmail")
		self.assertEqual(browse.formatItem(gmail, "name"), "Open Gmail")

	def test_help_lists_items_after_usage(self):
		text = browse.buildHelpText([item("Open Gmail", "kb:g")], "nameKey")
		self.assertTrue(text.startswith("Up and down arrows"))
		self.assertTrue(text.endswith("Open Gmail, g"))


class BrowseSettingsTests(unittest.TestCase):
	def setUp(self):
		temp = tempfile.TemporaryDirectory()
		self.addCleanup(temp.cleanup)
		self.path = str(Path(temp.name) / "config.json")

	def write(self, settings):
		config = {"version": 3, "settings": settings, "items": [storedItem("a", "kb:a")]}
		Path(self.path).write_text(json.dumps(config), encoding="utf-8")

	def test_old_config_gets_disabled_defaults(self):
		self.write({"verbosity": "advanced"})
		settings = cm.ConfigManager(self.path).getSettings()
		self.assertEqual(settings["verbosity"], "advanced")
		self.assertIs(settings["browseEnabled"], False)
		self.assertEqual((settings["browseFormat"], settings["browseOrder"]), ("nameKey", "list"))

	def test_settings_roundtrip_in_one_save(self):
		self.write({})
		manager = cm.ConfigManager(self.path)
		manager.updateSettings(browseEnabled=True, browseFormat="keyName", browseOrder="key")
		settings = cm.ConfigManager(self.path).getSettings()
		self.assertEqual(
			(settings["browseEnabled"], settings["browseFormat"], settings["browseOrder"]),
			(True, "keyName", "key"),
		)

	def test_invalid_browse_settings_rejected(self):
		for settings in ({"browseFormat": "loud"}, {"browseOrder": 1}, {"browseEnabled": "yes"}):
			self.write(settings)
			with self.assertRaises(ValueError):
				io.loadConfigFromPathStrict(self.path)
		self.write({})
		with self.assertRaises(ValueError):
			cm.ConfigManager(self.path).updateSettings(browseFormat="loud")
		with self.assertRaises(ValueError):
			cm.ConfigManager(self.path).updateSettings(unknown=True)


class BrowseLayerTests(unittest.TestCase):
	def setUp(self):
		temp = tempfile.TemporaryDirectory()
		self.addCleanup(temp.cleanup)
		self.path = str(Path(temp.name) / "config.json")
		self.messages = []
		self.addCleanup(patch.stopall)
		patch.object(ui, "message", side_effect=self.messages.append).start()
		self.browseable = Mock()
		patch.object(ui, "browseableMessage", self.browseable, create=True).start()
		self.bound = {}
		self.app = "explorer"

	def makePlugin(self, items, enabled=True):
		config = {
			"version": 3,
			"settings": {"browseEnabled": enabled},
			"items": items,
		}
		Path(self.path).write_text(json.dumps(config), encoding="utf-8")
		instance = plugin.GlobalPlugin.__new__(plugin.GlobalPlugin)
		globalPluginHandler.GlobalPlugin.__init__(instance)
		instance._enabled = True
		instance.verbosityLevel = "beginner"
		instance.instantMode = False
		instance.gestureToItems = {}
		instance.loadedCommandCount = 0
		instance.layerItems = []
		instance.browseGestureScripts = {}
		instance._resetBrowseState()
		instance._keepLayerOpen = False
		instance.configManager = cm.ConfigManager(self.path)
		instance.executionQueue = Mock()
		instance.bindGestures = self.bound.update
		instance.clearGestureBindings = self.bound.clear
		instance.getCurrentAppName = lambda: self.app
		instance.queueTone = lambda *a: None
		instance._getGesturesForScript = lambda description, fallback: fallback
		instance.activateInstantMode(speak=False)
		return instance

	def press(self, instance, scriptName, gestureId="kb:x"):
		"""Run a bound script through getScript, as NVDA does, so layer closing is exercised."""
		gesture = types.SimpleNamespace(identifiers=[gestureId])
		with patch.object(
			globalPluginHandler.GlobalPlugin,
			"getScript",
			lambda self, g: getattr(self, "script_" + scriptName),
		):
			instance.getScript(gesture)(gesture)

	def test_disabled_binds_no_browse_keys(self):
		instance = self.makePlugin([storedItem("a", "kb:a")], enabled=False)
		self.assertNotIn("kb:downarrow", self.bound)
		self.assertNotIn("kb:tab", self.bound)
		self.assertTrue(instance.instantMode)

	def test_item_keeps_its_key_and_other_browse_keys_still_bind(self):
		self.makePlugin([storedItem("Tab item", "kb:tab"), storedItem("Help item", "kb:h")])
		self.assertEqual(self.bound["kb:tab"], "runInstantItem")
		self.assertEqual(self.bound["kb:h"], "runInstantItem")
		self.assertEqual(self.bound["kb:downarrow"], "browseNext")
		self.assertEqual(self.bound["kb:f1"], "browseHelp")

	def test_browse_wraps_keeps_layer_open_and_enter_runs(self):
		instance = self.makePlugin([storedItem("One", "kb:1"), storedItem("Two", "kb:2")])
		self.press(instance, "browsePrevious")
		self.press(instance, "browseNext")
		self.press(instance, "browseNext")
		self.assertEqual(self.messages, ["Two, 2", "One, 1", "Two, 2"])
		self.assertTrue(instance.instantMode)
		self.press(instance, "browseActivate")
		instance.executionQueue.submit.assert_called_once()
		self.assertEqual(instance.executionQueue.submit.call_args.args[0]["name"], "Two")
		self.assertFalse(instance.instantMode)

	def test_enter_before_browsing_closes_layer_without_running(self):
		instance = self.makePlugin([storedItem("One", "kb:1")])
		self.press(instance, "browseActivate")
		instance.executionQueue.submit.assert_not_called()
		self.assertFalse(instance.instantMode)

	def test_other_app_item_on_browse_key_falls_back_to_browsing(self):
		instance = self.makePlugin(
			[storedItem("Notepad tab", "kb:tab", "notepad"), storedItem("One", "kb:1")]
		)
		self.press(instance, "runInstantItem", "kb(desktop):tab")
		self.assertEqual(self.messages, ["One, 1"])
		self.assertTrue(instance.instantMode)
		instance.executionQueue.submit.assert_not_called()

	def test_help_opens_list_and_closes_layer(self):
		instance = self.makePlugin([storedItem("One", "kb:1"), storedItem("Word", "kb:w", "winword")])
		self.press(instance, "browseHelp")
		text = self.browseable.call_args.args[0]
		self.assertIn("One, 1", text)
		self.assertNotIn("Word", text)
		self.assertFalse(instance.instantMode)

	def test_no_usable_items_says_so(self):
		instance = self.makePlugin([storedItem("Word", "kb:w", "winword")])
		self.press(instance, "browseNext")
		self.assertEqual(self.messages, ["No items are available in this application."])
		self.assertTrue(instance.instantMode)


if __name__ == "__main__":
	unittest.main()
