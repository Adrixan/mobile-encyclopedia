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

    # Search for "opensuse"
    results = model.filter_items(query="opensuse")
    assert len(results) > 0
    assert any("opensuse" in i.id.lower() for i in results)

    # Filter category
    admin_results = model.filter_items(category="admin")
    assert len(admin_results) > 0
    assert all(i.category == "admin" for i in admin_results)
