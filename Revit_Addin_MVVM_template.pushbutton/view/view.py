# -*- coding: utf-8 -*-
"""
View layer: WPF UI + event wiring.
"""

import clr

clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
from System.Windows.Controls import ListBoxItem
from pyrevit import script, forms
from Autodesk.Revit.UI import TaskDialog
import System

from common.language_manager import LanguageManager

xaml_file = script.get_bundle_file("view\\ui.xaml")


class TemplateWindow(forms.WPFWindow):
    def __init__(self, viewmodel):
        forms.WPFWindow.__init__(self, xaml_file)
        self.vm = viewmodel
        self.lang = LanguageManager()
        self.Title = self.lang.get_string("window_title")
        self.Loaded += self._on_loaded

    def _on_loaded(self, sender, e):
        self._find_controls()
        self._set_texts()
        self._bind_events()
        self._load_data()

    def _find_controls(self):
        self.search = self.FindName("SearchBox")
        self.check_all = self.FindName("CheckAllButton")
        self.uncheck_all = self.FindName("UncheckAllButton")
        self.toggle = self.FindName("ToggleCheckButton")
        self.list = self.FindName("ItemList")
        self.selected_panel = self.FindName("SelectedPanel")
        self.run_btn = self.FindName("RunButton")
        self.cancel_btn = self.FindName("CancelButton")

    def _set_texts(self):
        self._set_text("SelectItemTitle", "select_item_title")
        self._set_text("SearchTitle", "search")
        self._set_text("ListTitle", "item_list")
        self._set_text("SelectedTitle", "selected_items")
        self._btn_text(self.check_all, "check_all")
        self._btn_text(self.uncheck_all, "uncheck_all")
        self._btn_text(self.toggle, "toggle_check")
        self._btn_text(self.run_btn, "confirm")
        self._btn_text(self.cancel_btn, "cancel")

    def _set_text(self, name, key):
        el = self.FindName(name)
        if el:
            el.Text = self.lang.get_string(key)

    def _btn_text(self, btn, key):
        if btn:
            btn.Content = self.lang.get_string(key)

    def _bind_events(self):
        if self.search:
            self.search.TextChanged += self._on_search
        if self.check_all:
            self.check_all.Click += self._check_all
        if self.uncheck_all:
            self.uncheck_all.Click += self._uncheck_all
        if self.toggle:
            self.toggle.Click += self._toggle
        if self.list:
            self.list.SelectionChanged += self._on_select
        if self.run_btn:
            self.run_btn.Click += self._on_run
        if self.cancel_btn:
            self.cancel_btn.Click += self._on_cancel

    def _load_data(self):
        self._refresh_list(self.vm.items)
        self._update_selected()

    def _refresh_list(self, items):
        self.list.Items.Clear()
        for item in items:
            li = ListBoxItem()
            li.Content = item.to_display()
            li.Tag = item.Id
            li.IsSelected = item.Id in self.vm.selected_ids
            self.list.Items.Add(li)

    def _update_selected(self):
        self.selected_panel.Children.Clear()
        for li in self.list.SelectedItems:
            from System.Windows.Controls import TextBlock

            tb = TextBlock()
            tb.Text = li.Content
            self.selected_panel.Children.Add(tb)

    def _on_select(self, s, e):
        self.vm.selected_ids = set(li.Tag for li in self.list.SelectedItems)
        self._update_selected()

    def _on_search(self, s, e):
        self._refresh_list(self.vm.filter_items(self.search.Text))

    def _check_all(self, s, e):
        self.list.SelectAll()
        self._update_selected()

    def _uncheck_all(self, s, e):
        self.list.UnselectAll()
        self._update_selected()

    def _toggle(self, s, e):
        sel = list(self.list.SelectedItems)
        if len(sel) == self.list.Items.Count:
            self.list.UnselectAll()
        else:
            self.list.SelectAll()
            for i in sel:
                self.list.SelectedItems.Remove(i)
        self._update_selected()

    def _on_run(self, s, e):
        self.Hide()
        if self.vm.run_action():
            TaskDialog.Show(
                self.lang.get_string("success"), self.lang.get_string("action_success")
            )
        self._safe_result(True)
        self.Close()

    def _on_cancel(self, s, e):
        self._safe_result(False)
        self.Close()

    def _safe_result(self, val):
        try:
            if self.IsLoaded:
                self.DialogResult = val
        except Exception:
            pass
