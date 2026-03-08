# -*- coding: utf-8 -*-
"""
LanguageManager: multilingual support via system UI culture detection.

Loads translations from ``common/locales/translations.json`` (tabular JSON).
Falls back to embedded English strings if the file is missing or unreadable.

Usage:
    lang = LanguageManager()
    text = lang.get_string("window_title")
    text = lang.get_string("error_occurred", error=str(e))
"""

import clr
import codecs
import json
import os
from System.Globalization import CultureInfo
from System.IO import Path


class LanguageManager:
    """Manages multilingual support for the Revit application."""

    # Map .NET culture codes -> bundle keys used in translations.json
    LANGUAGE_CODES = {
        "en-US": "en_us",
        "en-GB": "en_gb",
        "fr-FR": "fr_fr",
        "de-DE": "de_de",
        "es-ES": "es_es",
        "nl-NL": "nl_nl",
        "it-IT": "it_it",
        "zh-CN": "chinese_s",
        "zh-TW": "chinese_t",
        "pl-PL": "pl",
        "ru-RU": "ru",
        "hu-HU": "hu",
        "cs-CZ": "cs",
        "bg-BG": "bg",
    }

    def __init__(self):
        self._cached_language_data = None
        self._current_language = None
        self._translations = None

    def _get_language_folder_path(self):
        """Get path to the language folder."""
        try:
            current_dir = Path.GetDirectoryName(os.path.abspath(__file__))
            return Path.Combine(current_dir, "locales")
        except Exception:
            return None

    def _get_translations_path(self):
        """Get path to the translations.json file."""
        try:
            folder_path = self._get_language_folder_path()
            if folder_path:
                return Path.Combine(folder_path, "translations.json")
        except Exception:
            return None

    def _get_current_language_code(self):
        """Detect the current language code from the system UI culture."""
        try:
            current_culture = str(CultureInfo.CurrentUICulture)

            # Exact match first
            bundle_key = self.LANGUAGE_CODES.get(current_culture)
            if bundle_key:
                return bundle_key

            # Two-letter fallback (e.g., "de" matches "de-DE")
            two_letter_code = current_culture.split("-")[0].lower()
            for culture_code, bundle_code in self.LANGUAGE_CODES.items():
                if culture_code.lower().startswith(two_letter_code):
                    return bundle_code

            return "en_us"
        except Exception:
            return "en_us"

    def _load_translations(self):
        """Load and parse the translations.json file (tabular format)."""
        try:
            if self._translations is not None:
                return self._translations

            file_path = self._get_translations_path()
            if not file_path or not os.path.exists(file_path):
                return None

            with codecs.open(file_path, "r", encoding="utf-8") as f:
                tabular_data = json.load(f)

                # Convert tabular [{key, en_us, de_de, ...}, ...] to
                # {lang: {key: text, ...}, ...} for efficient lookup
                translations = {}
                for row in tabular_data:
                    key = row.get("key")
                    if key:
                        for lang_code in self.LANGUAGE_CODES.values():
                            if lang_code not in translations:
                                translations[lang_code] = {}
                            translations[lang_code][key] = row.get(lang_code, key)

                self._translations = translations
                return translations

        except Exception:
            return None

    def get_language_data(self):
        """Return the translation dict for the current UI culture."""
        try:
            current_lang_code = self._get_current_language_code()

            # Return cached data if available
            if (
                self._cached_language_data
                and self._current_language == current_lang_code
            ):
                return self._cached_language_data

            # Load translations
            translations = self._load_translations()
            if translations and current_lang_code in translations:
                self._cached_language_data = translations[current_lang_code]
                self._current_language = current_lang_code
                return self._cached_language_data

            # Fallback to English
            if (
                translations
                and current_lang_code != "en_us"
                and "en_us" in translations
            ):
                self._cached_language_data = translations["en_us"]
                self._current_language = "en_us"
                return self._cached_language_data

            # Last resort: embedded English
            return self.get_embedded_english()

        except Exception:
            return self.get_embedded_english()

    def get_string(self, key, **kwargs):
        """Get a localized string with optional ``{named}`` parameter substitution.

        Args:
            key (str): Translation key (e.g., "window_title").
            **kwargs: Named parameters to substitute (e.g., error="some text").

        Returns:
            str: The localized string, or the raw key if lookup fails.
        """
        try:
            language_data = self.get_language_data()
            text = language_data.get(key, key)

            if kwargs:
                text = text.format(**kwargs)

            return text
        except Exception:
            return key

    def get_embedded_english(self):
        """Fallback English strings embedded in the code.

        These are GENERIC template strings. When creating a new button,
        update these to match your tool's terminology.
        """
        return {
            # -- Window --
            "window_title": "Template Tool",
            # -- Section titles --
            "select_item_title": "1. Select Items",
            "select_apply_list": "2. Configure Action",
            "search": "Search:",
            "item_list": "Item List:",
            "selected_items": "Selected Items:",
            # -- Buttons --
            "check_all": "Check all",
            "uncheck_all": "Uncheck all",
            "toggle_check": "Toggle check",
            "confirm": "Confirm",
            "cancel": "Cancel",
            "browse": "Browse...",
            # -- Status --
            "warning": "Warning",
            "error": "Error",
            "success": "Success",
            "loading": "Loading...",
            # -- Validation --
            "select_item_warning": "Please select at least one item.",
            "select_option_warning": "Please select an option.",
            "action_success": "Action completed successfully.",
            # -- Errors --
            "no_document": "No active document found.",
            "error_occurred": "An error occurred: {error}",
            "error_confirming": "Error confirming selection: {error}",
            "error_getting_items": "Error getting items: {error}",
            "error_loading_data": "Error loading data: {error}",
            "error_filtering": "Error filtering items: {error}",
            "error_updating_selection": "Error updating selections",
            # -- Transaction --
            "transaction_name": "Template Action",
        }
