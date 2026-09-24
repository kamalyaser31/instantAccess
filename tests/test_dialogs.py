import types
import unittest
from unittest.mock import Mock, patch

from nvda_stubs import dialogs, gui, wx
from auditcore.command_picker_dialog import NvdaCommandPickerDialog
from auditcore.nvda_commands import NvdaCommand


class DialogTests(unittest.TestCase):
	def test_action_test_preserves_delay_and_uses_shared_queue(self):
		for actionType, textAction, preDelay in (
			("TextSnippets", "type", 3),
			("TextSnippets", "copy", 0),
			("Keystrokes", "type", 3),
		):
			with self.subTest(actionType=actionType, textAction=textAction):
				action = {"type": actionType, "path": "a", "textAction": textAction, "delay": 2}
				dialog = types.SimpleNamespace(validate=Mock(return_value=action), executionQueue=Mock())
				with patch.object(gui, "messageBox", return_value=wx.YES):
					dialogs.InstantAccessActionDialog.onTestAction(dialog, None)
				dialog.executionQueue.submit.assert_called_once_with(
					{"actions": [action], "stopOnError": True}, preDelay=preDelay
				)

	def test_declining_action_test_does_not_queue_it(self):
		dialog = types.SimpleNamespace(
			validate=Mock(return_value={"type": "Keystrokes"}), executionQueue=Mock()
		)
		with patch.object(gui, "messageBox", return_value=wx.NO):
			dialogs.InstantAccessActionDialog.onTestAction(dialog, None)
		dialog.executionQueue.submit.assert_not_called()

	def test_ui_delay_accepts_zero_and_rejects_nonfinite(self):
		with patch.object(gui, "messageBox"):
			for value in ("nan", "inf", "-1", "1e300"):
				self.assertIsNone(
					dialogs.InstantAccessActionDialog._parseDelayField(None, value, "invalid", "negative")
				)
			self.assertEqual(
				dialogs.InstantAccessActionDialog._parseDelayField(None, "0", "invalid", "negative"), 0
			)

	def test_picker_preserves_selected_command_and_keeps_other_categories_lazy(self):
		dialog = NvdaCommandPickerDialog.__new__(NvdaCommandPickerDialog)
		dialog._isDestroyed = False
		dialog.tree = Mock()
		items = []

		def append(parent, label):
			item = Mock()
			item.GetID.return_value = len(items)
			items.append((label, item))
			return item

		dialog.tree.AppendItem.side_effect = append
		dialog.filterCtrl = Mock()
		dialog.filterCtrl.GetValue.return_value = ""
		dialog.okButton = Mock()
		dialog.commands = [
			NvdaCommand("A", "First", "m", "C", "first"),
			NvdaCommand("B", "Second", "m", "C", "second"),
		]
		dialog.populateTree("m|C|second")
		self.assertEqual(dialog.selectedCommandId, "m|C|second")
		dialog.okButton.Enable.assert_called_with(True)
		self.assertEqual(dialog._populatedCategories, {"B"})
		self.assertNotIn("First", [label for label, item in items])
		dialog.filterCtrl.GetValue.return_value = "no matching command"
		dialog.populateTree(dialog.selectedCommandId)
		self.assertEqual(dialog.selectedCommandId, "")
		dialog.okButton.Enable.assert_called_with(False)

	def test_child_destroy_does_not_cancel_picker(self):
		dialog = NvdaCommandPickerDialog.__new__(NvdaCommandPickerDialog)
		dialog._isDestroyed = False
		dialog._loadFuture = Mock()
		dialog._filterCallLater = Mock()
		event = Mock()
		dialog.onDestroy(event)
		self.assertFalse(dialog._isDestroyed)
		dialog._loadFuture.cancel.assert_not_called()
		event.GetEventObject.return_value = dialog
		dialog.onDestroy(event)
		self.assertTrue(dialog._isDestroyed)
		dialog._loadFuture.cancel.assert_called_once()
