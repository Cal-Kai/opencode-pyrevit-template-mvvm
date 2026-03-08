# -*- coding: utf-8 -*-
"""
Entry point for pyRevit pushbutton.
Bootstrap: clears cache -> imports -> instantiate Model/ViewModel/View -> ShowDialog.
"""

import sys

for mod_name in list(sys.modules.keys()):
    if mod_name.split(".")[0] in ("view", "viewmodel", "model", "common"):
        del sys.modules[mod_name]

from pyrevit import revit, forms
from model.model import TemplateModel
from viewmodel.viewmodel import TemplateViewModel
from view.view import TemplateWindow
from common.language_manager import LanguageManager

doc = revit.doc


def main(doc):
    lang = LanguageManager()
    if not doc:
        forms.alert(lang.get_string("no_document"), exitscript=True)
        return

    try:
        model = TemplateModel(doc)
        viewmodel = TemplateViewModel(model)
        window = TemplateWindow(viewmodel)
        window.ShowDialog()
    except Exception as e:
        forms.alert(lang.get_string("error_occurred", error=str(e)), exitscript=True)


if __name__ == "__main__":
    main(doc)
