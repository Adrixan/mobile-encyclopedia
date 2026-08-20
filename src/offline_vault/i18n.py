"""Localization and internationalization engine for offline-vault."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

DEFAULT_LOCALE = "en"
_CURRENT_LOCALE = DEFAULT_LOCALE
_TRANSLATIONS: Dict[str, Dict[str, str]] = {}


def get_locales_dir() -> Path:
    """Return the path to the locales directory."""
    return Path(__file__).parent / "locales"


def load_locale(locale: str) -> Dict[str, str]:
    """Load translation mapping for a given locale."""
    global _TRANSLATIONS
    if locale in _TRANSLATIONS:
        return _TRANSLATIONS[locale]

    locale_path = get_locales_dir() / f"{locale}.json"
    if not locale_path.is_file():
        fallback_path = get_locales_dir() / f"{DEFAULT_LOCALE}.json"
        if fallback_path.is_file():
            with open(fallback_path, "r", encoding="utf-8") as f:
                _TRANSLATIONS[locale] = json.load(f)
                return _TRANSLATIONS[locale]
        return {}

    with open(locale_path, "r", encoding="utf-8") as f:
        _TRANSLATIONS[locale] = json.load(f)
    return _TRANSLATIONS[locale]


def set_locale(locale: str) -> None:
    """Set the active locale."""
    global _CURRENT_LOCALE
    _CURRENT_LOCALE = locale
    load_locale(locale)


def get_locale() -> str:
    """Get the active locale."""
    return _CURRENT_LOCALE


def t(key: str, **kwargs: Any) -> str:
    """Translate a key with optional formatting arguments."""
    translations = load_locale(_CURRENT_LOCALE)
    template = translations.get(key)
    if template is None:
        # Fallback to English
        en_translations = load_locale(DEFAULT_LOCALE)
        template = en_translations.get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template
