"""Unit and security acceptance tests for US2.1: Master Catalog & Schema Validation."""

from pathlib import Path
import pytest

from offline_vault.catalog import (
    ResourceItem,
    ResourceCatalog,
    load_catalog,
    validate_resource_item,
)


def test_us2_1_load_default_catalog():
    catalog = load_catalog()
    assert len(catalog.items) > 0
    categories = catalog.get_categories()
    assert "Distro & Admin" in categories or "admin" in [c.lower() for c in categories]


def test_us2_1_all_required_domains_present():
    catalog = load_catalog()
    item_ids = {item.id for item in catalog.items}

    # Verify key items
    assert any("opensuse" in item_id for item_id in item_ids)
    assert any("archwiki" in item_id for item_id in item_ids)
    assert any("powershell" in item_id or "windows" in item_id for item_id in item_ids)
    assert any("php" in item_id for item_id in item_ids)
    assert any("javascript" in item_id or "mdn" in item_id for item_id in item_ids)
    assert any("xkcd" in item_id for item_id in item_ids)
    assert any("smbc" in item_id for item_id in item_ids)
    assert any("map" in item_id or "osm" in item_id for item_id in item_ids)

    # Verify all 8 languages are represented
    languages = {item.language for item in catalog.items}
    for lang in ["en", "es", "bs", "hr", "sr", "sl", "fr", "ar"]:
        assert lang in languages, f"Language {lang} missing from catalog"


def test_us2_1_schema_validation_security_rejects_unsafe_url():
    """Mandatory Security: Only HTTPS protocols allowed for upstream resources."""
    unsafe_item = {
        "id": "unsafe-res",
        "name": "Unsafe Resource",
        "category": "dev",
        "language": "en",
        "format": "zim",
        "size_mb": 100,
        "upstream_url": "http://insecure-site.org/archive.zim",
    }
    with pytest.raises(ValueError, match="Insecure or invalid URL protocol"):
        validate_resource_item(unsafe_item)


def test_us2_1_filter_by_language():
    catalog = load_catalog()
    bs_items = catalog.filter(language="bs")
    assert len(bs_items) > 0
    assert all(item.language == "bs" for item in bs_items)


def test_us2_1_filter_by_category():
    catalog = load_catalog()
    admin_items = catalog.filter(category="admin")
    assert len(admin_items) > 0


def test_us2_1_search_query():
    catalog = load_catalog()
    results = catalog.search("openSUSE")
    assert len(results) > 0
    assert any("opensuse" in r.name.lower() or "opensuse" in r.id.lower() for r in results)


def test_us2_1_calculate_selected_size():
    catalog = load_catalog()
    selected_ids = [catalog.items[0].id, catalog.items[1].id]
    expected_size = catalog.items[0].size_mb + catalog.items[1].size_mb
    assert catalog.calculate_total_size_mb(selected_ids) == expected_size
