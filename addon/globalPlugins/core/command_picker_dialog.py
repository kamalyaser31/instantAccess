# -*- coding: utf-8 -*-

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from locale import strxfrm
import addonHandler
import gui
from gui import guiHelper
import wx

from .constants import ERROR_CAPTION
from .nvda_commands import getAllActiveNvdaCommands

addonHandler.initTranslation()
_COMMAND_LOADER = ThreadPoolExecutor(max_workers=1, thread_name_prefix="instantAccessCommandPicker")


class NvdaCommandPickerDialog(wx.Dialog):
	def __init__(self, parent, selectedCommandId=""):
		# Translators: Title of the dialog used to select an NVDA command.
		wx.Dialog.__init__(self, parent, title=_("Select NVDA command"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
		self.selectedCommandId = selectedCommandId or ""
		self.commands = []
		self._commandById = {}
		self._filteredGrouped = {}
		self._populatedCategories = set()
		self._itemToCommandId = {}
		self._isDestroyed = False
		self._loadFuture = None
		self._filterCallLater = None
		self._isPopulatingTree = False

		mainSizer = wx.BoxSizer(wx.VERTICAL)
		sizerHelper = guiHelper.BoxSizerHelper(self, wx.VERTICAL)

		# Translators: Label for filter field in NVDA command selection dialog.
		self.filterCtrl = sizerHelper.addLabeledControl(_("Filter"), wx.TextCtrl)
		self.tree = wx.TreeCtrl(
			self,
			style=wx.TR_HAS_BUTTONS | wx.TR_HIDE_ROOT | wx.TR_LINES_AT_ROOT | wx.TR_SINGLE | wx.BORDER_SUNKEN,
		)
		sizerHelper.addItem(self.tree, flag=wx.EXPAND, proportion=1)

		buttonHelper = guiHelper.ButtonHelper(wx.HORIZONTAL)
		# Translators: Label for OK button in NVDA command selection dialog.
		self.okButton = buttonHelper.addButton(self, wx.ID_OK, _("&OK"))
		# Translators: Label for Cancel button in NVDA command selection dialog.
		buttonHelper.addButton(self, wx.ID_CANCEL, _("&Cancel"))

		mainSizer.Add(sizerHelper.sizer, 1, wx.ALL | wx.EXPAND, 10)
		mainSizer.Add(buttonHelper.sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)
		self.SetMinSize((520, 420))
		self.SetSizerAndFit(mainSizer)

		self.filterCtrl.Bind(wx.EVT_TEXT, self.onFilterChange)
		self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.onTreeSelectionChanged)
		self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.onTreeItemActivated)
		self.tree.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.onTreeItemExpanding)
		self.okButton.Bind(wx.EVT_BUTTON, self.onOk)
		self.Bind(wx.EVT_WINDOW_DESTROY, self.onDestroy)

		self.filterCtrl.Enable(False)
		self.tree.Enable(False)
		self.okButton.Enable(False)

		self.filterCtrl.SetFocus()
		self.CentreOnScreen()
		self._loadCommandsAsync()

	def onDestroy(self, event):
		self._isDestroyed = True
		if self._filterCallLater is not None:
			try:
				self._filterCallLater.Stop()
			except Exception:
				pass
			self._filterCallLater = None
		event.Skip()

	def _isTreeAlive(self):
		if self._isDestroyed or not hasattr(self, "tree"):
			return False
		try:
			self.tree.GetId()
			return True
		except Exception:
			return False

	def _loadCommandsAsync(self):
		self._loadFuture = _COMMAND_LOADER.submit(getAllActiveNvdaCommands)
		self._loadFuture.add_done_callback(lambda future: wx.CallAfter(self._onCommandsLoaded, future))

	def _onCommandsLoaded(self, future):
		if not self._isTreeAlive():
			return
		try:
			self.commands = future.result()
		except Exception:
			self.commands = []
		self._commandById = {command.identifier: command for command in self.commands}
		self.filterCtrl.Enable(True)
		self.tree.Enable(True)
		self.populateTree(self.selectedCommandId)

	def _groupCommands(self, filterText):
		grouped = defaultdict(list)
		words = [word.strip().lower() for word in (filterText or "").split(" ") if word.strip()]
		for command in self.commands:
			searchText = f"{command.category} {command.displayName}".lower()
			if words and not all(word in searchText for word in words):
				continue
			grouped[command.category].append(command)
		return grouped

	def populateTree(self, preferredCommandId=""):
		if not self._isTreeAlive():
			return
		self._isPopulatingTree = True
		self.tree.Freeze()
		try:
			self.tree.DeleteAllItems()
			root = self.tree.AddRoot("root")
			self._itemToCommandId = {}
			self._populatedCategories = set()
			self._filteredGrouped = self._groupCommands(self.filterCtrl.GetValue())
			for category in sorted(self._filteredGrouped.keys(), key=strxfrm):
				categoryItem = self.tree.AppendItem(root, category)
				# Placeholder child ensures categories are expandable while keeping startup fast.
				self.tree.AppendItem(categoryItem, "")
			self.tree.CollapseAll()
		finally:
			self.tree.Thaw()
			self._isPopulatingTree = False
		self.selectedCommandId = ""
		self.okButton.Enable(False)

	def onFilterChange(self, event):
		if not self._isTreeAlive():
			return
		if self._filterCallLater is not None:
			try:
				self._filterCallLater.Stop()
			except Exception:
				pass
		self._filterCallLater = wx.CallLater(120, self._applyFilter)

	def _applyFilter(self):
		if not self._isTreeAlive():
			return
		hadFilterFocus = self.FindFocus() == self.filterCtrl
		insertionPoint = self.filterCtrl.GetInsertionPoint()
		selectionStart, selectionEnd = self.filterCtrl.GetSelection()
		self.populateTree(self.selectedCommandId)
		if hadFilterFocus and self.filterCtrl:
			self.filterCtrl.SetFocus()
			self.filterCtrl.SetInsertionPoint(insertionPoint)
			self.filterCtrl.SetSelection(selectionStart, selectionEnd)

	def onTreeItemExpanding(self, event):
		if not self._isTreeAlive():
			return
		item = event.GetItem()
		if not item or not item.IsOk():
			return
		category = self.tree.GetItemText(item)
		if not category or category not in self._filteredGrouped:
			return
		if category in self._populatedCategories:
			return
		commands = self._filteredGrouped.get(category, [])
		self.tree.Freeze()
		try:
			self.tree.DeleteChildren(item)
			for command in sorted(commands, key=lambda c: strxfrm(c.displayName)):
				commandItem = self.tree.AppendItem(item, command.displayName)
				self._itemToCommandId[commandItem.GetID()] = command.identifier
			self._populatedCategories.add(category)
		finally:
			self.tree.Thaw()
		self._updateSelectionState()

	def onTreeSelectionChanged(self, event):
		if not self._isTreeAlive():
			return
		if self._isPopulatingTree:
			return
		self._updateSelectionState(event.GetItem())

	def onTreeItemActivated(self, event):
		if not self._isTreeAlive():
			return
		item = event.GetItem()
		commandId = self._getCommandIdForItem(item)
		if commandId:
			self.selectedCommandId = commandId
			self.onOk(event)

	def _updateSelectionState(self, item=None):
		if not self._isTreeAlive():
			return
		if item is None or not item.IsOk():
			item = self.tree.GetSelection()
		if (item is None or not item.IsOk()) and hasattr(self.tree, "GetFocusedItem"):
			try:
				item = self.tree.GetFocusedItem()
			except Exception:
				item = None
		commandId = self._getCommandIdForItem(item)
		if commandId:
			self.selectedCommandId = commandId
			self.okButton.Enable(True)
		else:
			self.selectedCommandId = ""
			self.okButton.Enable(False)

	def _getCommandIdForItem(self, item):
		if not self._isTreeAlive():
			return ""
		if not item or not item.IsOk():
			return ""
		commandId = self._itemToCommandId.get(item.GetID(), "")
		if commandId:
			return commandId
		if self.tree.ItemHasChildren(item):
			return ""
		parent = self.tree.GetItemParent(item)
		if not parent or not parent.IsOk():
			return ""
		category = self.tree.GetItemText(parent)
		name = self.tree.GetItemText(item)
		if not category or not name:
			return ""
		for command in self._filteredGrouped.get(category, []):
			if command.displayName == name:
				return command.identifier
		return ""

	def onOk(self, event):
		if not self.selectedCommandId:
			gui.messageBox(_("Please select an NVDA command."), ERROR_CAPTION, wx.OK | wx.ICON_ERROR)
			return
		command = self._commandById.get(self.selectedCommandId)
		commandLabel = command.label if command else self.selectedCommandId
		self.result = {"commandId": self.selectedCommandId, "commandLabel": commandLabel}
		self.EndModal(wx.ID_OK)
