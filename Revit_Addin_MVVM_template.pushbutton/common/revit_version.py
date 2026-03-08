# -*- coding: utf-8 -*-
def get_revit_version_number(app):
    """
    Return the major Revit version as int (e.g., 2023), or None if unknown.
    Compatible with IronPython 2.7.
    """
    try:
        if app is None:
            return None
        ver = app.VersionNumber
        if not ver:
            return None
        return int(ver)
    except Exception:
        return None


def warn_if_version_mismatch(app, min_version, warning_text):
    """
    Print a warning if current Revit version is below min_version.
    Use this for API behaviors that changed across versions.
    """
    try:
        ver = get_revit_version_number(app)
        if ver is None:
            return
        if ver < int(min_version):
            print("WARNING: {0} (Current: {1})".format(warning_text, ver))
    except Exception:
        pass


def warn_common_api_changes(app):
    """
    Print common warnings for API behaviors that changed across versions.
    Customize per tool.
    """
    ver = get_revit_version_number(app)
    if ver is None:
        return

    # Revit 2024: ElementId.IntegerValue can fail on 64-bit ids; use ElementId.Value.
    if ver >= 2024:
        print("WARNING: Revit 2024+ uses 64-bit ElementId. Prefer ElementId.Value over IntegerValue.")

    # Revit 2022+: ParameterType and BuiltInParameterGroup are deprecated in favor of ForgeTypeId.
    if ver >= 2022:
        print("WARNING: Revit 2022+ deprecates ParameterType; use ForgeTypeId (SpecTypeId).")
    if ver >= 2024:
        print("WARNING: Revit 2024+ deprecates BuiltInParameterGroup; use GroupTypeId.")
