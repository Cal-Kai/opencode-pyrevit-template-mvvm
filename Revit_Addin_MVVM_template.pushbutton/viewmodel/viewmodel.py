# -*- coding: utf-8 -*-
"""
ViewModel layer: state, validation, orchestration.
"""

import os
import sys
from Autodesk.Revit.UI import TaskDialog

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.language_manager import LanguageManager


class TemplateViewModel:
    def __init__(self, model):
        self.model = model
        self.lang = LanguageManager()
        self.items = []
        self.selected_ids = set()
        self.load_data()

    def load_data(self):
        self.items = self.model.get_items()

    def filter_items(self, search_text):
        if not search_text:
            return self.items
        search = search_text.lower()
        return [i for i in self.items if search in i.to_display().lower()]

    def validate_selection(self):
        if not self.selected_ids:
            TaskDialog.Show(
                self.lang.get_string("warning"),
                self.lang.get_string("select_item_warning"),
            )
            return False
        return True

    def run_action(self):
        if not self.validate_selection():
            return False
        selected = [i for i in self.items if i.Id in self.selected_ids]
        try:
            return self.model.apply_action(selected)
        except Exception as e:
            TaskDialog.Show(
                self.lang.get_string("error"),
                self.lang.get_string("error_occurred", error=str(e)),
            )
            return False

    def cleanup(self):
        self.items = []
        self.selected_ids = set()
        self.model.cleanup()
