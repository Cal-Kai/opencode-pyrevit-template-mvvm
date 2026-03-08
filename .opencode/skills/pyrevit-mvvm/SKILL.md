---
name: pyrevit-mvvm-template
description: pyRevit MVVM template for pushbutton tools (IronPython 2.7, pyRevit 6.x). Use when creating or editing pyRevit buttons with Model-View-ViewModel pattern.
---

# pyRevit MVVM Template

Template for building pyRevit pushbutton tools with MVVM pattern.

## Environment (locked)

| Constraint | Value |
|------------|-------|
| pyRevit | 6.x |
| Python | IronPython 2.7 |
| f-strings | Forbidden (use `.format()`) |
| Type hints | Forbidden |

## Folder layout

```
MyTool.pushbutton/
    bundle.yaml
    icon.png
    script.py              # Bootstrap only
    model/
        __init__.py
        model.py           # Revit API, transactions, data
    viewmodel/
        __init__.py
        viewmodel.py       # State, validation, orchestration
    view/
        __init__.py
        view.py            # WPF + events
        ui.xaml            # UI layout
    common/
        __init__.py
        language_manager.py
        locales/
            translations.json
```

## MVVM separation

| Layer | Responsibility | Never contains |
|-------|----------------|-----------------|
| **Model** | Revit API, Transaction, data access | UI logic |
| **ViewModel** | State, validation, calls Model | WPF imports |
| **View** | WPF UI, events, delegates to VM | Business logic |
| **script.py** | Bootstrap + error handling | Business logic |

## Bootstrap (script.py)

```python
import sys
for mod_name in list(sys.modules.keys()):
    if mod_name.split('.')[0] in ("view", "viewmodel", "model", "common"):
        del sys.modules[mod_name]

from model.model import TemplateModel
from viewmodel.viewmodel import TemplateViewModel
from view.view import TemplateWindow

def main(doc):
    model = TemplateModel(doc)
    viewmodel = TemplateViewModel(model)
    window = TemplateWindow(viewmodel)
    window.ShowDialog()
```

## Core patterns

### Safe helpers (model.py)

```python
def safe_get_name(obj, fallback="<unnamed>"):
    try:
        return obj.Name if obj and obj.Name else fallback
    except Exception:
        return fallback

def safe_element_id_value(eid):
    try:
        return eid.Value  # Revit 2024+
    except AttributeError:
        return eid.IntegerValue  # Older
```

### Cached property (model.py)

```python
class TemplateModel:
    def __init__(self, doc):
        self._cache = {}

    @property
    def items(self):
        if 'items' not in self._cache:
            self._cache['items'] = self.get_items()
        return self._cache['items']
```

### Transaction (model.py)

```python
def apply_action(self, selected_items):
    tx_name = self.lang.get_string("transaction_name")
    with Transaction(self.doc, tx_name) as t:
        try:
            t.Start()
            # mutations
            t.Commit()
            return True
        except Exception as e:
            if t.GetStatus() == TransactionStatus.Started:
                t.RollBack()
            raise
```

### ViewModel state (viewmodel.py)

```python
class TemplateViewModel:
    def __init__(self, model):
        self.model = model
        self.items = []
        self.selected_ids = set()
        self.load_data()

    def run_action(self):
        selected = [i for i in self.items if i.Id in self.selected_ids]
        return self.model.apply_action(selected)
```

### View events (view.py)

```python
class TemplateWindow(forms.WPFWindow):
    def __init__(self, viewmodel):
        forms.WPFWindow.__init__(self, xaml_file)
        self.vm = viewmodel
        self.Loaded += self._on_loaded

    def _on_loaded(self, sender, e):
        self._find_controls()
        self._bind_events()
        self._load_data()

    def _on_run(self, s, e):
        if self.vm.run_action():
            TaskDialog.Show("Success", "Done")
        self.Close()
```

## Creating a new button

1. Copy `Revit_Addin_MVVM_template.pushbutton` → rename
2. Update `bundle.yaml`
3. Rename classes: `TemplateModel` → `MyToolModel`, etc.
4. Implement `get_items()` in Model
5. Implement `apply_action()` with Transaction
6. Customize `ui.xaml` as needed

## Localization

All UI strings via `LanguageManager`:
- Add keys to `translations.json`
- Add to `get_embedded_english()` in `language_manager.py`
- Use: `self.lang.get_string("key")`
