"""Tests for TUI state management and budget calculation logic."""

import pytest
from offline_vault.catalog import load_catalog
from offline_vault.tui import TUIStateModel


def test_us4_1_tui_state_model_toggle():
    catalog = load_catalog()
    model = TUIStateModel(catalog=catalog, total_free_bytes=100 * 1024 * 1024 * 1024)  # 100 GB

    first_item = catalog.items[0]
    assert first_item.id not in model.selected_ids

    model.toggle_item(first_item.id)
    assert first_item.id in model.selected_ids
    assert model.get_selected_size_mb() == first_item.size_mb

    model.toggle_item(first_item.id)
    assert first_item.id not in model.selected_ids
    assert model.get_selected_size_mb() == 0


def test_us4_1_tui_budget_meter_warning():
    catalog = load_catalog()
    # Tiny free space: 100 MB
    model = TUIStateModel(catalog=catalog, total_free_bytes=100 * 1024 * 1024)

    # Select large Wikipedia item (5500 MB)
    wiki_item = catalog.get_by_id("wikipedia_en_top100k")
    if wiki_item:
        model.toggle_item(wiki_item.id)
        assert model.is_over_budget() is True
        remaining_mb = model.get_projected_remaining_mb()
        assert remaining_mb < 0


def test_us4_1_tui_filter_items():
    catalog = load_catalog()
    model = TUIStateModel(catalog=catalog, total_free_bytes=50 * 1024 * 1024 * 1024)

    # Search for "termux"
    results = model.filter_items(query="termux")
    assert len(results) > 0
    assert any("termux" in i.id.lower() for i in results)

    # Filter category
    admin_results = model.filter_items(category="admin")
    assert len(admin_results) > 0
    assert all(i.category == "admin" for i in admin_results)

    # Filter tools category
    tools_results = model.filter_items(category="tools")
    assert len(tools_results) >= 5
    assert all(i.category == "tools" for i in tools_results)


def test_toggle_keeps_cursor_position(tmp_path):
    import asyncio

    from textual.widgets import DataTable

    from offline_vault.config import VaultConfig
    from offline_vault.tui import OfflineVaultApp

    async def scenario():
        app = OfflineVaultApp(config=VaultConfig(vault_dir=str(tmp_path)))
        async with app.run_test(size=(160, 50)) as pilot:
            table = app.query_one("#catalog_table", DataTable)
            table.focus()
            await pilot.pause()
            for _ in range(5):
                await pilot.press("down")
            await pilot.press("space")
            await pilot.pause()
            assert table.cursor_row == 5
            assert app.current_rows[5].id in app.model.selected_ids
            assert table.get_cell_at((5, 0)) == "[X]"
            await pilot.press("slash")
            await pilot.pause()
            assert app.focused.id == "search_input"
            table.focus()
            await pilot.pause()
            await pilot.press("question_mark")
            await pilot.pause()
            assert type(app.screen).__name__ == "HelpScreen"
            await pilot.press("escape")
            await pilot.pause()
            assert type(app.screen).__name__ != "HelpScreen"

    asyncio.run(scenario())


def test_r_refreshes_catalog_and_reloads_table(tmp_path, monkeypatch):
    import asyncio

    from offline_vault import catalog_builder
    from offline_vault.catalog import get_default_catalog_file, get_user_catalog_file
    from offline_vault.catalog_builder import BuildReport
    from offline_vault.config import VaultConfig
    from offline_vault.tui import OfflineVaultApp

    def fake_refresh(cache_dir=None, force=False, log=None):
        user = get_user_catalog_file()
        user.parent.mkdir(parents=True, exist_ok=True)
        user.write_text(get_default_catalog_file().read_text(encoding="utf-8").replace("size_mb: 37", "size_mb: 99", 1),
                        encoding="utf-8")
        return BuildReport(items=134)

    monkeypatch.setattr(catalog_builder, "refresh_user_catalog", fake_refresh)

    async def scenario():
        app = OfflineVaultApp(config=VaultConfig(vault_dir=str(tmp_path)))
        async with app.run_test(size=(160, 50)) as pilot:
            app.query_one("#catalog_table").focus()
            await pilot.press("r")
            for _ in range(50):
                await pilot.pause(0.05)
                if app.catalog.get_by_id("archwiki_en").size_mb == 99:
                    break
            assert app.catalog.get_by_id("archwiki_en").size_mb == 99
            assert app.model.catalog is app.catalog

    asyncio.run(scenario())
