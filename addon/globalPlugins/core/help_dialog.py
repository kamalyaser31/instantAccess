# -*- coding: utf-8 -*-

import addonHandler
from gui import guiHelper
import wx

from .browse import formatItem, matchesFilter

addonHandler.initTranslation()


class HelpListDialog(wx.Dialog):
	def __init__(self, parent, items, browseFormat="nameKey"):
		# Translators: Title of the window listing instant Access items available in the current application.
		super().__init__(
			parent,
			title=_("instant Access items"),
			style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
		)
		self.allItems = list(items)
		self.filteredItems = list(items)
		self.browseFormat = browseFormat
		self.selectedItem = None

		mainSizer = wx.BoxSizer(wx.VERTICAL)
		sizerHelper = guiHelper.BoxSizerHelper(self, wx.VERTICAL)

		# Translators: Label for filter field in instant Access help dialog.
		self.filterCtrl = sizerHelper.addLabeledControl(_("&Filter:"), wx.TextCtrl)

		# Translators: Label for items list in instant Access help dialog.
		itemsLabel = wx.StaticText(self, wx.ID_ANY, _("&Items:"))
		sizerHelper.addItem(itemsLabel)
		self.listBox = wx.ListBox(self, wx.ID_ANY, style=wx.LB_SINGLE)
		sizerHelper.addItem(self.listBox, flag=wx.EXPAND, proportion=1)

		buttonHelper = guiHelper.ButtonHelper(wx.HORIZONTAL)
		# Translators: Button to run the selected instant Access item.
		self.runButton = buttonHelper.addButton(self, wx.ID_OK, _("&Run"))
		# Translators: Button to cancel and close the dialog without running anything.
		self.cancelButton = buttonHelper.addButton(self, wx.ID_CANCEL, _("&Cancel"))
		self.runButton.SetDefault()

		mainSizer.Add(sizerHelper.sizer, 1, wx.ALL | wx.EXPAND, 10)
		mainSizer.Add(buttonHelper.sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)
		self.SetMinSize((480, 360))
		self.SetSizerAndFit(mainSizer)

		self.filterCtrl.Bind(wx.EVT_TEXT, self.onFilterChange)
		self.listBox.Bind(wx.EVT_LISTBOX_DCLICK, self.onItemActivated)
		self.runButton.Bind(wx.EVT_BUTTON, self.onRun)

		self._updateList()

	def _updateList(self):
		query = self.filterCtrl.GetValue().strip()
		self.filteredItems = [item for item in self.allItems if matchesFilter(item, query)]
		labels = [formatItem(item, self.browseFormat) for item in self.filteredItems]
		self.listBox.Set(labels)
		if self.filteredItems:
			self.listBox.SetSelection(0)
			self.runButton.Enable(True)
		else:
			self.runButton.Enable(False)

	def onFilterChange(self, event):
		self._updateList()

	def onItemActivated(self, event):
		self.onRun(event)

	def onRun(self, event):
		selection = self.listBox.GetSelection()
		if selection != wx.NOT_FOUND and 0 <= selection < len(self.filteredItems):
			self.selectedItem = self.filteredItems[selection]
			self.EndModal(wx.ID_OK)
