# Revit Add-in MVVM Template

Template for building pyRevit pushbutton tools with MVVM pattern.

---

## Environment (locked)

| Constraint | Value |
|---|---|
| pyRevit | `6.0.x` |
| Python engine | **IronPython 2.7** (not CPython) |
| f-strings | **Forbidden** (Python 3.6+). Use `"{0}".format(...)` |
| Type hints | **Forbidden** (Python 3.5+) |
| async/await | **Forbidden** (Python 3.5+) |
| C-extensions | **Not supported** by IronPython |
| CPython hashbang | Do **not** use `#! python3` |

---

## Folder Layout

```
MyTool.pushbutton/
    bundle.yaml                  # Localized title, tooltip (pyRevit 5.2+)
    icon.png                     # Button icon (optionally icon.dark.png)
    script.py                    # Entry point (bootstrap only)
    README.md                    # This guide
    model/
        __init__.py              # Empty
        model.py                 # Revit API + transactions + data wrappers
    viewmodel/
        __init__.py              # Empty
        viewmodel.py             # Validation, state, orchestration
    view/
        __init__.py              # Empty
        view.py                  # WPF window + event wiring
        ui.xaml                  # WPF layout
    common/
        __init__.py              # Empty
        language_manager.py      # Multilingual support via system UI culture
        revit_version.py         # Revit version detection + warnings
        locales/
            translations.json    # Tabular translation data (14 languages)
```

---

## MVVM Pattern (required)

Every button MUST follow this separation:

| Layer | Responsibility | Never contains |
|---|---|---|
| **Model** (`model.py`) | Revit API calls, `Transaction` boundaries, data access, wrapper objects | UI logic, WPF imports |
| **ViewModel** (`viewmodel.py`) | Validation, state management, orchestration; calls Model methods | Revit API calls, WPF imports |
| **View** (`view.py` + `ui.xaml`) | WPF UI + event wiring; delegates logic to ViewModel | Revit API calls (except `TaskDialog`), business logic |
| **script.py** | Bootstrap + top-level error handling only | Business logic of any kind |

### Bootstrap flow (`script.py`)

```
1. Clear cached local modules     (CRITICAL - see "Module Cache" below)
2. Import Model, ViewModel, View
3. Resolve shared utilities on sys.path (e.g., usage statistics)
4. Guard against missing `doc`
5. Instantiate:  Model(doc) -> ViewModel(model) -> View(viewmodel)
6. ShowDialog()
7. Centralized try/except with localized error message
```

---

## Architecture

ViewModel inherits from `object`. State is stored as plain attributes (`self.items`, `self.selected_ids`). The View reads/writes these directly and refreshes the UI manually via event handlers wired with `button.Click += self.handler`.

```python
# viewmodel.py
class MyViewModel(object):
    def __init__(self, model):
        self.model = model
        self.items = []
        self.selected_ids = set()
```

This approach is used by all 9 proven buttons in the repo. It is simple, debuggable, and works reliably with IronPython + pyRevit.

---

## Critical Patterns (from proven buttons)

### 1. Module Cache Clearing

**Problem:** pyRevit reuses the IronPython engine across buttons. If two buttons both have `model/model.py`, the second button may load the first button's cached module.

**Solution:** Every `script.py` MUST start with this block before any local imports:

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

### 2. XAML Loading

Always load XAML via `script.get_bundle_file(...)`:

```python
from pyrevit import script, forms

xaml_file = script.get_bundle_file("view\\ui.xaml")

class MyWindow(forms.WPFWindow):
    def __init__(self, viewmodel):
        forms.WPFWindow.__init__(self, xaml_file)
```

### 3. Safe `.Name` Access

Revit elements can throw when accessing `.Name` (e.g., some family wrappers, deleted elements). Always guard:

```python
# In Model -- use safe_get_name()
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

In wrapper objects, expose a `to_display()` method. In View, always prefer `item.to_display()` over `item.Name`.

### 4. Safe `ElementId` Access

Revit 2024+ uses 64-bit `ElementId`; in Revit 2026 `IntegerValue` was **removed** and only `Value` exists. Use a **try/except** pattern so the fallback is never evaluated when it would raise.

**Do not use `getattr` with a fallback to `IntegerValue`:**

```python
# WRONG — in Revit 2026 this raises: 'ElementId' object has no attribute 'IntegerValue'
# Python evaluates the third argument before getattr runs, so eid.IntegerValue is always evaluated.
getattr(assembly.Id, 'Value', assembly.Id.IntegerValue)
```

**Use try/except instead:**

```python
def safe_element_id_value(element_id):
    try:
        return element_id.Value          # Revit 2024+ / 2026
    except AttributeError:
        try:
            return element_id.IntegerValue   # Older versions
        except Exception:
            return None
```

When you need an integer id inline (e.g. for list item `Tag` or set membership), use the same pattern so `IntegerValue` is never accessed in Revit 2026:

```python
try:
    assembly_id = int(assembly.Id.Value)
except AttributeError:
    assembly_id = int(assembly.Id.IntegerValue)
list_item.Tag = assembly_id
```

### 5. Safe `BuiltInParameterGroup` / `GroupTypeId` for Parameter Operations

`BuiltInParameterGroup` was deprecated in Revit 2024+ and may be removed in future versions. The replacement is `GroupTypeId`. Code that unconditionally imports or uses `BuiltInParameterGroup` will break on newer Revit versions, and code that only uses `GroupTypeId` will break on older ones.

**Do not import `BuiltInParameterGroup` unconditionally:**

```python
# WRONG — will crash if BuiltInParameterGroup is removed in a future Revit version
from Autodesk.Revit.DB import BuiltInParameterGroup
family_manager.AddParameter(param_def, BuiltInParameterGroup.INVALID, False)
```

**Use guarded imports and a helper that tries both APIs:**

```python
# At module level — guarded imports
try:
    from Autodesk.Revit.DB import GroupTypeId
except Exception:
    GroupTypeId = None

try:
    from Autodesk.Revit.DB import BuiltInParameterGroup
except Exception:
    BuiltInParameterGroup = None

# Helper function
def _get_parameter_group_invalid():
    """Returns the appropriate 'invalid' parameter group for the current Revit version."""
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
```

**Usage in AddParameter / ReplaceParameter:**

```python
param_group = _get_parameter_group_invalid()
if param_group is None:
    raise Exception("No compatible parameter group type available in this Revit version.")
family_manager.AddParameter(param_def, param_group, is_instance)
```

Note: Using guarded imports prevents crashes when the deprecated enum is removed in future Revit versions.

### 6. Cached Property Pattern

Avoid re-querying Revit on every property access:

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
        """Call when the dialog closes."""
        self._items_cache = None
```

### 6. Deferred Loading (Loading Indicator)

For tools that load large datasets, show the window immediately with a loading indicator, then load data after the window renders:

```python
# In View.__init__:
self.loading_indicator = self.FindName("LoadingIndicator")
self.Loaded += self._on_window_loaded

# In View._on_window_loaded:
def _on_window_loaded(self, sender, e):
    try:
        if self.loading_indicator:
            self.loading_indicator.Visibility = System.Windows.Visibility.Visible
        self._initialize_data()
    finally:
        if self.loading_indicator:
            self.loading_indicator.Visibility = System.Windows.Visibility.Collapsed
```

The XAML template includes a `LoadingIndicator` overlay (`Border` with `ProgressBar`) ready to use.

### 7. Toggle Check Button

Inverts the current ListBox selection:

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

### 8. Safe `DialogResult` Setting

When the window is hidden before a long operation (e.g., Revit transaction), setting `DialogResult` can throw `InvalidOperationException`:

```python
def _set_dialog_result_safe(self, value):
    try:
        if self.IsLoaded:
            self.DialogResult = value
    except Exception:
        pass
```

### 9. Transaction Pattern

All Revit document mutations MUST be wrapped in a `Transaction`. On failure, roll back and raise a localized message:

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

### 10. Config Persistence

For tools that need to remember user settings (e.g., last save path):

```python
from pyrevit import script

cfg = script.get_config()

# Read
last_path = cfg.get_option("last_save_path", "")

# Write
cfg.last_save_path = selected_path
script.save_config()
```

### 11. Usage Statistics Logging

Production buttons log usage frequency via a shared utility. Uncomment in `script.py` when your extension has it:

```python
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
from statistics_utils.get_usage_frequency import log_usage_frequency

log_usage_frequency(__file__)
```

---

## Localization

### Rules

1. **All user-visible strings** must come from `LanguageManager`, backed by `common/locales/translations.json`.
2. **Never hardcode UI text** in Python. Set text in `view.py` using `lang_manager.get_string(...)`.
3. Embedded English in `get_embedded_english()` serves as last-resort fallback. Keep it generic.

### How it works

1. `LanguageManager` detects the system UI culture via `CultureInfo.CurrentUICulture`.
2. Maps it to a bundle key (e.g., `de-DE` -> `de_de`).
3. Loads `translations.json` (tabular format: `[{key, en_us, de_de, ...}, ...]`).
4. Falls back: current language -> `en_us` -> embedded English.

### Adding a new translation key

1. Add the key + all 14 language values to `translations.json`.
2. Add the same key + English value to `get_embedded_english()` in `language_manager.py`.
3. Use it: `lang_manager.get_string("my_new_key", param=value)`.

### Supported languages

`en_us`, `en_gb`, `fr_fr`, `de_de`, `es_es`, `nl_nl`, `it_it`, `chinese_s`, `chinese_t`, `pl`, `ru`, `hu`, `cs`, `bg`

---

## Revit Version Safety

### Helpers provided

| Helper | Location | Purpose |
|---|---|---|
| `safe_element_id_value(eid)` | `model.py` | Handles 64-bit `ElementId` (Revit 2024+) |
| `safe_get_name(obj)` | `model.py` | Guards `.Name` access |
| `safe_get_param_value_as_string(elem, bip)` | `model.py` | Guards `BuiltInParameter` access |
| `is_point_based_level_family(fam)` | `model.py` | Checks `FamilyPlacementType` before placement |
| `get_revit_version_number(app)` | `revit_version.py` | Returns major version as `int` |
| `warn_if_version_mismatch(app, min, text)` | `revit_version.py` | Prints warning if below minimum |
| `warn_common_api_changes(app)` | `revit_version.py` | Prints known API deprecation warnings |

### Known version pitfalls

| Version | Change |
|---|---|
| Revit 2024+ | `ElementId` is 64-bit. Use `.Value` instead of `.IntegerValue`. |
| Revit 2026+ | `ElementId.IntegerValue` **removed**; use `.Value` only. Do **not** use `getattr(eid, 'Value', eid.IntegerValue)` — the default is evaluated before `getattr` runs, so in 2026 it raises. Use try/except (see Pattern #4). |
| Revit 2022+ | `ParameterType` deprecated. Use `ForgeTypeId` / `SpecTypeId`. |
| Revit 2024+ | `BuiltInParameterGroup` deprecated. Use `GroupTypeId`. |
| Revit 2022+ | `FamilyPlacementType` check required before `NewFamilyInstance`. |

Version warnings are gated by `ENABLE_VERSION_WARNINGS` in `script.py` (default `False`). Enable during development.

---

## Step-by-Step: Creating a New Button

### 1. Copy the template

Duplicate the entire `Revit_Addin_MVVM_template.pushbutton` folder. Rename it to `MyTool.pushbutton`.

### 2. Update `bundle.yaml`

```yaml
title:
  en_us: "My Tool"
  de_de: "Mein Werkzeug"
tooltip:
  en_us: "Does something useful"
  de_de: "Macht etwas Nützliches"
```

### 3. Replace `icon.png`

Provide a 32x32 or 96x96 PNG. Optionally add `icon.dark.png` for dark themes.

### 4. Rename classes

| File | Old class name | New class name |
|---|---|---|
| `model.py` | `TemplateModel` | `MyToolModel` |
| `model.py` | `TemplateItem` | `MyToolItem` (or domain-specific name) |
| `viewmodel.py` | `TemplateViewModel` | `MyToolViewModel` |
| `view.py` | `TemplateWindow` | `MyToolWindow` |
| `script.py` | Update all three import references | Match the new names |

### 5. Implement the Model

1. Replace the dummy `get_items()` with real `FilteredElementCollector` logic.
2. Wrap each result in a `MyToolItem` with `to_display()`.
3. Implement `apply_action()` with the actual Revit transaction.
4. Add any additional cached properties needed.

```python
def get_items(self):
    collector = FilteredElementCollector(self.doc)
    elements = collector.OfClass(Wall).ToElements()
    return [MyToolItem(safe_element_id_value(e.Id), safe_get_name(e))
            for e in elements]
```

### 6. Implement the ViewModel

1. Add validation rules in `validate_selection()` or add new validators.
2. Add any state attributes needed (text inputs, combo selections).

### 7. Customize the View

1. Edit `ui.xaml`: add tool-specific controls to the right panel (the `<!-- TODO -->` section).
2. In `view.py`:
   - Add `FindName()` calls for new controls in `_find_controls()`.
   - Add localized text in `_set_localized_texts()`.
   - Wire new event handlers in `_setup_event_handlers()`.

### 8. Update translations

1. Add new keys to `translations.json` (all 14 languages).
2. Add the same keys to `get_embedded_english()` in `language_manager.py`.

### 9. Update the module cache list

In `script.py`, add any new submodules to the cache-clearing block:

```python
for mod_name in list(sys.modules.keys()):
    if mod_name in (
        "view", "view.view",
        "viewmodel", "viewmodel.viewmodel",
        "model", "model.model",
        "common", "common.language_manager",
        # Add new submodules here:
        # "model.my_helper",
    ):
        del sys.modules[mod_name]
```

### 10. Test

1. Reload pyRevit (or use pyRevit's "Reload" button).
2. Open a Revit project with relevant elements.
3. Click your button and verify:
   - Window opens without errors.
   - Items load correctly.
   - Search/filter works.
   - Check all / Uncheck all / Toggle check work.
   - Confirm executes the transaction.
   - Cancel closes cleanly.
   - Language detection works (change Windows display language to verify).

---

## XAML Template Features

The provided `ui.xaml` includes:

| Feature | Element name | Notes |
|---|---|---|
| Loading overlay | `LoadingIndicator` | `ProgressBar` + text, collapsed by default |
| Search box | `SearchBox` | `TextBox` with `TextChanged` event |
| Item list | `ItemList` | `ListBox` with virtualization enabled |
| Bulk selection | `CheckAllButton`, `UncheckAllButton`, `ToggleCheckButton` | Three buttons |
| Selection summary | `SelectedPanel` | `StackPanel` showing selected items |
| Action buttons | `RunButton`, `CancelButton` | Primary (orange) + secondary (gray) styles |
| Right panel | Empty `StackPanel` | Placeholder for tool-specific controls |

### Brand colors

- Primary: `#FF6B00` (orange), hover: `#E66000`
- Secondary: `#666666` (gray), hover: `#555555`
- Background: `#F5F5F5`

### Adding controls to the right panel

The right panel (`Grid.Column="2"`) is a placeholder. Common control patterns:

- **Text inputs**: `TextBox` for prefix/suffix, file paths
- **Dropdowns**: `ComboBox` for selections (title blocks, categories)
- **Checkboxes**: `CheckBox` for options (e.g., open file after export)
- **Multi-select**: Additional `ListBox` for complex selections

---

## Common Pitfalls & Solutions

### `.Name` throws on Revit wrappers

**Symptom:** `AttributeError` or COM exception when displaying element names.
**Solution:** Always use `to_display()` on wrapper objects or `safe_get_name()`.

### Stale modules from other buttons

**Symptom:** Wrong classes loaded, `AttributeError` on unexpected attributes, behavior from a different button.
**Solution:** Module cache clearing at the top of `script.py` (see Pattern #1).

### `ElementId` / `IntegerValue` in Revit 2026

**Symptom:** `'ElementId' object has no attribute 'IntegerValue'` when using a pattern like `getattr(assembly.Id, 'Value', assembly.Id.IntegerValue)`.
**Cause:** In Python, the third argument to `getattr()` is **evaluated before** `getattr` runs. So in Revit 2026, `assembly.Id.IntegerValue` is evaluated as the default and raises because `IntegerValue` was removed.
**Solution:** Use try/except: try `element_id.Value` first, then in `except AttributeError` use `element_id.IntegerValue`. See Pattern #4.

**Symptom:** Crash when setting `DialogResult` after hiding the window for a long operation.
**Solution:** Use `_set_dialog_result_safe()` (see Pattern #8).

### Name collisions when creating/duplicating elements

**Symptom:** Transaction fails because an element with the same name already exists.
**Solution:** Check for existing elements by name first. Reuse if found, then proceed with the rest of the operation.

### Stale element references after `EditFamily`/`LoadFamily`

**Symptom:** `ElementId` or object references become invalid after family editing.
**Solution:** Store **family/type names** (strings) before the operation. Re-fetch by name afterward.

### Family placement crashes

**Symptom:** `NewFamilyInstance` fails for hosted/face-based families.
**Solution:** Check `FamilyPlacementType` with `is_point_based_level_family()` before using point+level placement. Hosted and face-based families require different APIs.

### UI freezes on large datasets

**Symptom:** Window hangs for seconds before appearing.
**Solution:** Use the deferred loading pattern (Pattern #6). Show window immediately, load data in `_on_window_loaded`.

### `FamilySymbol` not active

**Symptom:** `InvalidOperationException` when placing instances of a newly created type.
**Solution:** Call `family_symbol.Activate()` before assignment or placement.

---

## File-by-File Reference

### `script.py`
- Lines 25-38: Module cache clearing (add new submodules here).
- Lines 43-51: Imports (rename classes when copying template).
- Lines 57-60: Usage statistics (uncomment when available).
- Lines 71-108: `main()` function with bootstrap flow.

### `model/model.py`
- `TemplateItem`: Data wrapper with `Id` and `to_display()`. Rename per tool.
- `safe_get_name()`, `safe_element_id_value()`, `safe_get_param_value_as_string()`: Cross-version helpers.
- `TemplateModel`: Cached properties, `get_items()`, `apply_action()`, `cleanup()`.

### `viewmodel/viewmodel.py`
- Inherits from `object`.
- `load_data()`: Called once during `__init__`.
- `filter_items()`: Search with safe display text.
- `validate_selection()`: Guards before action.
- `run_action()`: Validates, resolves items, delegates to Model.
- `cleanup()`: Releases resources on window close.

### `view/view.py`
- `TemplateWindow(forms.WPFWindow)`: Main window class.
- `_on_window_loaded()`: Deferred loading with loading indicator.
- `_find_controls()`: Stores XAML control references.
- `_set_localized_texts()`: Sets all UI text via `LanguageManager`.
- `_setup_event_handlers()`: Wires Click/TextChanged/SelectionChanged events.
- `toggle_check()`: Inverts selection.
- `_set_dialog_result_safe()`: Defensive `DialogResult` setter.

### `view/ui.xaml`
- Lines 1-109: Window resources (Button, SecondaryButton, TextBox, ListBox styles).
- Lines 128-144: Loading indicator overlay.
- Lines 149-202: Left panel (search + item list).
- Lines 207-229: Selected items panel.
- Lines 236-252: Right panel (tool-specific controls placeholder).
- Lines 257-273: Action buttons (Run + Cancel).

### `common/language_manager.py`
- `LANGUAGE_CODES`: Maps .NET culture codes to bundle keys.
- `_load_translations()`: Parses tabular JSON to `{lang: {key: text}}`.
- `get_string(key, **kwargs)`: Main API. Returns localized string with parameter substitution.
- `get_embedded_english()`: Last-resort fallback. Keep generic.

### `common/revit_version.py`
- `get_revit_version_number(app)`: Returns major version as `int`.
- `warn_if_version_mismatch()`: Warns if below a minimum version.
- `warn_common_api_changes()`: Prints known API deprecation warnings.

### `common/locales/translations.json`
- Tabular format: `[{key, en_us, de_de, fr_fr, ...}, ...]`.
- 14 languages per key.
- Add new keys here first, then add to `get_embedded_english()`.
