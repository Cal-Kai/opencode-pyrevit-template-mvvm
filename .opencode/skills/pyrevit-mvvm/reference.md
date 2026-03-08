# Revit Add-in MVVM Template — Reference

Detailed patterns and file-by-file reference. Use when implementing or debugging.

**Available MCP:** Use **revit-api-docs (windows)** or **revit-api-docs (with search-library enabled)** for Revit API lookups (classes, methods, enums). Check tool schemas in the project `mcps` folder before calling.

## 1. Module cache clearing (script.py)

Before any local imports:

```python
import sys

for mod_name in list(sys.modules.keys()):
    if mod_name in (
        "view", "view.view",
        "viewmodel", "viewmodel.viewmodel",
        "model", "model.model",
        "common", "common.language_manager",
    ):
        del sys.modules[mod_name]
```

Add any additional submodules your button introduces.

## 2. XAML loading

```python
from pyrevit import script, forms

xaml_file = script.get_bundle_file("view\\ui.xaml")

class MyWindow(forms.WPFWindow):
    def __init__(self, viewmodel):
        forms.WPFWindow.__init__(self, xaml_file)
```

## 3. Safe .Name access (Model)

```python
def safe_get_name(obj, fallback="<unnamed>"):
    try:
        if obj is None:
            return fallback
        value = obj.Name
        if value:
            return value
    except Exception:
        pass
    return fallback
```

In wrappers expose `to_display()`. In View use `item.to_display()` not `item.Name`.

## 4. Safe ElementId (Revit 2024+ / 2026)

**Do not use `getattr` with a fallback to `IntegerValue`.** In Python, the third argument to `getattr()` is evaluated **before** `getattr` runs. So in Revit 2026 (where `ElementId.IntegerValue` was removed), `getattr(assembly.Id, 'Value', assembly.Id.IntegerValue)` will **always** evaluate `assembly.Id.IntegerValue` as the default and raise `'ElementId' object has no attribute 'IntegerValue'`.

Use try/except so the fallback is only executed when `Value` is missing (older Revit):

```python
def safe_element_id_value(element_id):
    try:
        return element_id.Value          # Revit 2024+ / 2026
    except AttributeError:
        try:
            return element_id.IntegerValue   # Older
        except Exception:
            return None
```

Inline (e.g. for list item `Tag` or set membership):

```python
try:
    assembly_id = int(assembly.Id.Value)
except AttributeError:
    assembly_id = int(assembly.Id.IntegerValue)
```

## 5. Safe BuiltInParameterGroup / GroupTypeId (AddParameter/ReplaceParameter)

`BuiltInParameterGroup` is deprecated (Revit 2024+) and can be removed in newer versions. Use guarded imports and resolve a compatible `Invalid` group at runtime.

```python
try:
    from Autodesk.Revit.DB import GroupTypeId
except Exception:
    GroupTypeId = None

try:
    from Autodesk.Revit.DB import BuiltInParameterGroup
except Exception:
    BuiltInParameterGroup = None


def get_invalid_parameter_group():
    if GroupTypeId is not None:
        try:
            return GroupTypeId.Invalid
        except Exception:
            pass
    if BuiltInParameterGroup is not None:
        try:
            return BuiltInParameterGroup.INVALID
        except Exception:
            pass
    return None


param_group = get_invalid_parameter_group()
if param_group is None:
    raise Exception("No compatible parameter group type available in this Revit version.")

family_manager.AddParameter(param_def, param_group, is_instance)
# family_manager.ReplaceParameter(existing_param, param_def, param_group, is_instance)
```

Never unconditionally import `BuiltInParameterGroup` in shared scripts/modules that load on button startup.

## 6. Cached property (Model)

```python
class MyModel(object):
    def __init__(self, doc):
        self.doc = doc
        self._items_cache = None

    @property
    def items(self):
        if self._items_cache is None:
            self._items_cache = self._query_items()
        return self._items_cache

    def cleanup(self):
        self._items_cache = None
```

## 7. Deferred loading (View)

```python
# In View.__init__:
self.loading_indicator = self.FindName("LoadingIndicator")
self.Loaded += self._on_window_loaded

# In _on_window_loaded:
def _on_window_loaded(self, sender, e):
    try:
        if self.loading_indicator:
            self.loading_indicator.Visibility = System.Windows.Visibility.Visible
        self._initialize_data()
    finally:
        if self.loading_indicator:
            self.loading_indicator.Visibility = System.Windows.Visibility.Collapsed
```

## 8. Toggle check (View)

```python
def toggle_check(self, sender, e):
    currently_selected = list(self.list_box.SelectedItems)
    if len(currently_selected) == self.list_box.Items.Count:
        self.list_box.UnselectAll()
    else:
        self.list_box.SelectAll()
        for item in currently_selected:
            self.list_box.SelectedItems.Remove(item)
    self.update_selected_panel()
```

## 9. Safe DialogResult (View)

```python
def _set_dialog_result_safe(self, value):
    try:
        if self.IsLoaded:
            self.DialogResult = value
    except Exception:
        pass
```

## 10. Transaction pattern (Model)

```python
def apply_action(self, selected_items):
    tx_name = self.lang_manager.get_string("transaction_name")
    with Transaction(self.doc, tx_name) as t:
        try:
            t.Start()
            # ... Revit API mutations ...
            t.Commit()
            return True
        except Exception as e:
            if t.GetStatus() == TransactionStatus.Started:
                t.RollBack()
            raise Exception(
                self.lang_manager.get_string("error_occurred", error=str(e))
            )
```

## 11. Config persistence (script or ViewModel)

```python
from pyrevit import script

cfg = script.get_config()
last_path = cfg.get_option("last_save_path", "")
# ...
cfg.last_save_path = selected_path
script.save_config()
```

## 12. Usage statistics (script.py)

Uncomment when extension has the utility:

```python
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
from statistics_utils.get_usage_frequency import log_usage_frequency

log_usage_frequency(__file__)
```

---

## Localization

- All user-visible strings from `LanguageManager` and `translations.json`.
- Adding a key: add to `translations.json` (all 14 languages), add to `get_embedded_english()` in `language_manager.py`, then `lang_manager.get_string("key", param=value)`.

Supported languages: `en_us`, `en_gb`, `fr_fr`, `de_de`, `es_es`, `nl_nl`, `it_it`, `chinese_s`, `chinese_t`, `pl`, `ru`, `hu`, `cs`, `bg`.

---

## Revit version helpers

| Helper | Location | Purpose |
|--------|----------|---------|
| `safe_element_id_value(eid)` | model.py | 64-bit ElementId (2024+) |
| `safe_get_name(obj)` | model.py | Safe .Name |
| `safe_get_param_value_as_string(elem, bip)` | model.py | BuiltInParameter |
| `is_point_based_level_family(fam)` | model.py | Placement type check |
| `get_revit_version_number(app)` | revit_version.py | Major version int |
| `warn_if_version_mismatch(app, min, text)` | revit_version.py | Min version warning |
| `warn_common_api_changes(app)` | revit_version.py | API deprecation warnings |

Version pitfalls: 2024+ ElementId use `.Value`; **2026+ `IntegerValue` removed — do not use `getattr(eid, 'Value', eid.IntegerValue)` (default is evaluated before getattr, so it raises in 2026); use try/except.** 2022+ prefer `ForgeTypeId`/`SpecTypeId` over `ParameterType`; 2024+ `GroupTypeId` over `BuiltInParameterGroup`; 2022+ check `FamilyPlacementType` before `NewFamilyInstance`.

---

## File-by-file reference

- **script.py**: Lines ~25–38 cache clearing; ~43–51 imports; ~57–60 usage stats (optional); ~71–108 `main()` bootstrap.
- **model/model.py**: Item wrapper with `Id` and `to_display()`; helpers above; Model with cached props, `get_items()`, `apply_action()`, `cleanup()`.
- **viewmodel/viewmodel.py**: Inherits `object`; `load_data()`, `filter_items()`, `validate_selection()`, `run_action()`, `cleanup()`.
- **view/view.py**: WPFWindow subclass; `_on_window_loaded`, `_find_controls()`, `_set_localized_texts()`, `_setup_event_handlers()`, `toggle_check()`, `_set_dialog_result_safe()`.
- **view/ui.xaml**: LoadingIndicator, SearchBox, ItemList, CheckAll/UncheckAll/ToggleCheck, SelectedPanel, Run/Cancel, right panel placeholder. Brand: primary `#FF6B00`, secondary `#666666`, background `#F5F5F5`.
- **common/language_manager.py**: `LANGUAGE_CODES`, `_load_translations()`, `get_string(key, **kwargs)`, `get_embedded_english()`.
- **common/revit_version.py**: Version helpers as in table above.
- **common/locales/translations.json**: Tabular `[{key, en_us, de_de, ...}, ...]`, 14 languages.
