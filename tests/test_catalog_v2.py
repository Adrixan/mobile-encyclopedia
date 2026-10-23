"""Acceptance tests for US8.2: typed upstream sources and the Android-first catalog."""

import pytest

from offline_vault.catalog import load_catalog, validate_resource_item


def _base(**overrides):
    data = {
        "id": "sample_item",
        "name": "Sample",
        "category": "wiki",
        "language": "en",
        "format": "zim",
        "size_mb": 10,
        "upstream_url": "https://download.kiwix.org/zim/wikipedia/wikipedia_en_top_maxi_2026-09.zim",
    }
    data.update(overrides)
    return data


def test_kiwix_source_requires_book_name():
    with pytest.raises(ValueError, match="kiwix_name"):
        validate_resource_item(_base(source="kiwix"))


def test_kiwix_source_rejects_invalid_flavour():
    with pytest.raises(ValueError, match="flavour"):
        validate_resource_item(_base(source="kiwix", kiwix_name="wikipedia_en_top", kiwix_flavour="huge"))


def test_kiwix_source_parses_book_fields():
    item = validate_resource_item(_base(source="kiwix", kiwix_name="wikipedia_en_top", kiwix_flavour="maxi"))
    assert item.source == "kiwix"
    assert item.kiwix_name == "wikipedia_en_top"
    assert item.kiwix_flavour == "maxi"


def test_github_source_requires_repo_and_valid_pattern():
    with pytest.raises(ValueError, match="github_repo"):
        validate_resource_item(_base(source="github", format="zip", category="tools", asset_pattern=r".*\.zip"))
    with pytest.raises(ValueError, match="asset_pattern"):
        validate_resource_item(
            _base(source="github", format="zip", category="tools", github_repo="gchq/CyberChef", asset_pattern="(")
        )


def test_kolibri_source_requires_channel_id():
    with pytest.raises(ValueError, match="kolibri_channel"):
        validate_resource_item(_base(source="kolibri", format="kolibri", kolibri_channel="not-a-channel"))


def test_relative_paths_reject_traversal():
    for field in ("entrypoint", "extract_subdir"):
        with pytest.raises(ValueError, match=field):
            validate_resource_item(_base(format="zip", category="tools", **{field: "../etc/passwd"}))
        with pytest.raises(ValueError, match=field):
            validate_resource_item(_base(format="zip", category="tools", **{field: "/abs/path"}))


def test_unknown_source_rejected():
    with pytest.raises(ValueError, match="source"):
        validate_resource_item(_base(source="ftp"))


def test_catalog_has_no_duplicate_or_placeholder_urls():
    catalog = load_catalog()
    downloadable = [i for i in catalog.items if i.source == "url"]
    urls = [i.upstream_url for i in downloadable]
    assert len(urls) == len(set(urls)), "url-sourced items must not share an upstream URL"
    books = [(i.kiwix_name, i.kiwix_flavour) for i in catalog.items if i.source == "kiwix"]
    assert len(books) == len(set(books)), "two items resolve to the same Kiwix book"
    channels = [i.kolibri_channel for i in catalog.items if i.source == "kolibri"]
    assert len(channels) == len(set(channels))


def test_catalog_has_no_docsets_and_every_archive_has_an_entrypoint():
    catalog = load_catalog()
    assert not [i.id for i in catalog.items if i.format == "docset"]
    for item in catalog.items:
        if item.format in ("zip", "tar"):
            assert item.entrypoint, f"{item.id} needs an entrypoint for Android browsers"


def test_catalog_kiwix_items_use_typed_source():
    catalog = load_catalog()
    for item in catalog.items:
        if item.format == "zim":
            assert item.source == "kiwix", f"{item.id} should resolve through the Kiwix library"


def test_serve_root_flag_parsed_and_typed():
    item = validate_resource_item(_base(format="zip", category="tools", entrypoint="index.html", serve_root=True))
    assert item.serve_root is True
    with pytest.raises(ValueError, match="serve_root"):
        validate_resource_item(_base(format="zip", category="tools", serve_root="yes"))
