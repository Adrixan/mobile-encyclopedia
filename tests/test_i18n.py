"""Tests for the i18n localization module."""

from offline_vault.i18n import get_locale, load_locale, set_locale, t


def test_default_locale_is_english():
    set_locale("en")
    assert get_locale() == "en"
    assert t("app_name") == "Offline Vault"


def test_translation_formatting():
    set_locale("en")
    msg = t("vault_path", path="/media/vault")
    assert msg == "Vault Directory: /media/vault"


def test_spanish_translation():
    set_locale("es")
    assert t("btn_sync") == "Iniciar Sincronización"


def test_bosnian_translation():
    set_locale("bs")
    assert t("btn_sync") == "Pokreni sinhronizaciju"


def test_fallback_on_missing_key():
    set_locale("en")
    assert t("non_existent_key") == "non_existent_key"
