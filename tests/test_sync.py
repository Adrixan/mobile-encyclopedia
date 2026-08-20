"""Tests for SyncManager placement into category folders and Kiwix integration."""

from pathlib import Path
import pytest

from offline_vault.catalog import ResourceCatalog, ResourceItem
from offline_vault.config import VaultConfig
from offline_vault.sync import SyncManager


def test_sync_destination_matches_category(tmp_path):
    config = VaultConfig(vault_dir=str(tmp_path / "vault"))
    catalog = ResourceCatalog(
        [
            ResourceItem(
                id="xkcd_test",
                name="XKCD Test",
                category="fun",
                language="en",
                format="zim",
                size_mb=10,
                upstream_url="https://example.org/xkcd.zim",
            ),
            ResourceItem(
                id="python_test",
                name="Python Test",
                category="dev",
                language="en",
                format="docset",
                size_mb=15,
                upstream_url="https://example.org/Python_3.tgz",
            ),
            ResourceItem(
                id="opensuse_test",
                name="openSUSE Test",
                category="admin",
                language="en",
                format="zim",
                size_mb=20,
                upstream_url="https://example.org/opensuse.zim",
            ),
        ]
    )

    mgr = SyncManager(config, catalog)

    dest_xkcd = mgr.get_destination_for_item(catalog.get_by_id("xkcd_test"))
    assert dest_xkcd.parent.name == "fun"
    assert dest_xkcd.name == "xkcd.zim"

    dest_py = mgr.get_destination_for_item(catalog.get_by_id("python_test"))
    assert dest_py.parent.name == "dev"
    assert dest_py.name == "Python_3.tgz"

    dest_suse = mgr.get_destination_for_item(catalog.get_by_id("opensuse_test"))
    assert dest_suse.parent.name == "admin"
    assert dest_suse.name == "opensuse.zim"
