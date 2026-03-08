# pyRevit MVVM Template

Template and reference for building **pyRevit pushbutton tools** using the **Model–View–ViewModel (MVVM)** pattern. Use this repo to scaffold new buttons that stay maintainable and consistent with IronPython 2.7 and pyRevit 6.x.

---

## What’s in this repo

| Path | Purpose |
|------|--------|
| **`Revit_Addin_MVVM_template.pushbutton/`** | Copy this folder to create a new button. Full docs and patterns are in [its README](Revit_Addin_MVVM_template.pushbutton/README.md). |
| **`.opencode/skills/pyrevit-mvvm/`** | Skill and reference for AI/editor assistance when creating or editing pyRevit MVVM buttons. |

---

## Environment (locked)

| Constraint | Value |
|------------|-------|
| pyRevit | 6.x |
| Python | IronPython 2.7 |
| f-strings | Forbidden — use `.format()` |
| Type hints | Forbidden |

---

## Folder layout (template)

```
MyTool.pushbutton/
    bundle.yaml              # Localized title, tooltip
    icon.png
    script.py                # Bootstrap only
    model/
        model.py             # Revit API, transactions, data
    viewmodel/
        viewmodel.py         # State, validation, orchestration
    view/
        view.py              # WPF + events
        ui.xaml              # UI layout
    common/
        language_manager.py
        locales/
            translations.json
```

---

## MVVM separation

| Layer | Responsibility | Never contains |
|-------|----------------|----------------|
| **Model** | Revit API, Transaction, data access | UI logic |
| **ViewModel** | State, validation, calls Model | WPF imports |
| **View** | WPF UI, events, delegates to VM | Business logic |
| **script.py** | Bootstrap + error handling | Business logic |

---

## Creating a new button

1. **Copy** `Revit_Addin_MVVM_template.pushbutton` and rename the folder (e.g. `MyTool.pushbutton`).
2. **Update** `bundle.yaml` (title, tooltip).
3. **Rename** classes: `TemplateModel` → `MyToolModel`, `TemplateViewModel` → `MyToolViewModel`, `TemplateWindow` → `MyToolWindow`, and any item types (e.g. `TemplateItem` → `MyToolItem`).
4. **Implement** `get_items()` in the Model and `apply_action()` with a Transaction.
5. **Customize** `view/ui.xaml` and wire controls in `view/view.py` as needed.

For step-by-step instructions, Revit version safety, localization, and pitfalls, see **[Revit_Addin_MVVM_template.pushbutton/README.md](Revit_Addin_MVVM_template.pushbutton/README.md)**.

---

## Bootstrap (script.py)

`script.py` should only bootstrap and show the window:

1. Clear cached local modules (so pyRevit doesn’t reuse modules from other buttons).
2. Import Model, ViewModel, View.
3. Instantiate: `Model(doc)` → `ViewModel(model)` → `View(viewmodel)`.
4. Call `ShowDialog()` and handle errors at the top level.

---

## Localization

All user-visible strings go through `LanguageManager` and `common/locales/translations.json`. Add keys there and in `get_embedded_english()` in `language_manager.py`, then use `self.lang.get_string("key")` in code.

---

## License

See repository license file.
