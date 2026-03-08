# -*- coding: utf-8 -*-
"""
Model layer: Revit API calls, Transactions, data access.
"""

import os
import sys
from Autodesk.Revit.DB import Transaction, TransactionStatus, FilteredElementCollector

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.language_manager import LanguageManager


def safe_get_name(obj, fallback="<unnamed>"):
    try:
        return obj.Name if obj and obj.Name else fallback
    except Exception:
        return fallback


def safe_element_id_value(eid):
    try:
        return eid.Value
    except AttributeError:
        return eid.IntegerValue


class TemplateItem:
    def __init__(self, id, name):
        self.Id = id
        self.Name = name

    def to_display(self):
        return self.Name


class TemplateModel:
    def __init__(self, doc):
        self.doc = doc
        self.lang = LanguageManager()
        self._cache = {}

    @property
    def items(self):
        if "items" not in self._cache:
            self._cache["items"] = self.get_items()
        return self._cache["items"]

    def get_items(self):
        """Override with actual Revit query."""
        return [TemplateItem(i, "Item {0}".format(i)) for i in range(1, 11)]

    def apply_action(self, selected_items):
        """Override with actual Transaction logic."""
        tx_name = self.lang.get_string("transaction_name")
        with Transaction(self.doc, tx_name) as t:
            try:
                t.Start()
                # TODO: Revit API mutations
                t.Commit()
                return True
            except Exception as e:
                if t.GetStatus() == TransactionStatus.Started:
                    t.RollBack()
                raise Exception(self.lang.get_string("error_occurred", error=str(e)))

    def cleanup(self):
        self._cache.clear()
