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


def test_all_locales_have_the_same_keys_as_english():
    import json

    from offline_vault.i18n import get_locales_dir

    english = set(json.loads((get_locales_dir() / "en.json").read_text(encoding="utf-8")))
    for path in get_locales_dir().glob("*.json"):
        keys = set(json.loads(path.read_text(encoding="utf-8")))
        assert keys == english, f"{path.name}: missing {sorted(english - keys)}, extra {sorted(keys - english)}"
    assert {p.stem for p in get_locales_dir().glob("*.json")} >= {"en", "de", "es", "bs"}


def test_tui_uses_configured_locale(tmp_path):
    import asyncio

    from textual.widgets import Button

    from offline_vault.config import VaultConfig
    from offline_vault.tui import OfflineVaultApp

    async def scenario():
        app = OfflineVaultApp(config=VaultConfig(vault_dir=str(tmp_path), locale="de"))
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            assert "Pfad" in str(app.query_one("#btn_set_path", Button).label)
            assert "Verfügbar" in str(app.query_one("#budget_bar").render())
            assert str(app.query_one("#cat_fun", Button).label) == "Bücher"

    try:
        asyncio.run(scenario())
    finally:
        set_locale("en")


def test_locale_names_cannot_traverse_paths(tmp_path):
    import json
    import os

    from offline_vault.i18n import get_locales_dir

    planted = tmp_path / "evil.json"
    planted.write_text(json.dumps({"btn_quit": "PWNED"}), encoding="utf-8")
    traversal = os.path.relpath(planted.with_suffix(""), get_locales_dir())
    assert load_locale(traversal).get("btn_quit") != "PWNED"
    set_locale(traversal)
    assert t("btn_quit") == "Quit"
    set_locale("en")
