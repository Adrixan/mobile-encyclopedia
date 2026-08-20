"""Tests for SyncManager placement, canonical versionless naming, and safe atomic pruning."""

from pathlib import Path
from unittest.mock import MagicMock
import pytest

from offline_vault.catalog import ResourceCatalog, ResourceItem
from offline_vault.config import VaultConfig
from offline_vault.downloader import DownloadResult
from offline_vault.sync import SyncManager


def test_sync_destination_is_canonical_versionless(tmp_path):
    config = VaultConfig(vault_dir=str(tmp_path / "vault"))
    item = ResourceItem(
        id="xkcd_complete_comics",
        name="XKCD Complete Comics Archive",
        category="fun",
        language="en",
        format="zim",
        size_mb=10,
        upstream_url="https://lb.download.kiwix.org/zim/other/explainxkcd_en_all_maxi_2026-07.zim",
    )
    catalog = ResourceCatalog([item])
    mgr = SyncManager(config, catalog)

    dest = mgr.get_destination_for_item(item)
    assert dest.parent.name == "fun"
    # Canonical versionless name
    assert dest.name == "xkcd_complete_comics.zim"


def test_sync_prunes_old_version_only_after_success(tmp_path):
    vault_dir = tmp_path / "vault"
    config = VaultConfig(vault_dir=str(vault_dir))
    item = ResourceItem(
        id="xkcd_complete_comics",
        name="XKCD Test",
        category="fun",
        language="en",
        format="zim",
        size_mb=10,
        upstream_url="https://example.org/xkcd_latest.zim",
    )
    catalog = ResourceCatalog([item])
    mgr = SyncManager(config, catalog)

    fun_dir = vault_dir / "fun"
    fun_dir.mkdir(parents=True, exist_ok=True)

    # Place an old dated version and old canonical version
    old_dated = fun_dir / "explainxkcd_en_all_maxi_2024-01.zim"
    old_dated.write_text("old dated content")
    old_canonical = fun_dir / "xkcd_complete_comics.zim"
    old_canonical.write_text("old canonical v1")

    # Mock download success
    def mock_download(url, destination, **kwargs):
        dest_path = Path(destination)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text("new updated content v2")
        return DownloadResult(url=url, destination=dest_path, success=True, bytes_downloaded=22)

    mgr.engine.download = mock_download

    summary = mgr.sync_items(["xkcd_complete_comics"], force_update=True)
    assert summary.completed == 1

    # Canonical file now has new content
    assert old_canonical.exists()
    assert old_canonical.read_text() == "new updated content v2"

    # Old dated version was safely pruned
    assert not old_dated.exists()


def test_sync_preserves_old_version_if_download_fails(tmp_path):
    vault_dir = tmp_path / "vault"
    config = VaultConfig(vault_dir=str(vault_dir))
    item = ResourceItem(
        id="xkcd_complete_comics",
        name="XKCD Test",
        category="fun",
        language="en",
        format="zim",
        size_mb=10,
        upstream_url="https://example.org/xkcd_latest.zim",
    )
    catalog = ResourceCatalog([item])
    mgr = SyncManager(config, catalog)

    fun_dir = vault_dir / "fun"
    fun_dir.mkdir(parents=True, exist_ok=True)

    # Place working v1 file
    old_canonical = fun_dir / "xkcd_complete_comics.zim"
    old_canonical.write_text("working v1 content")

    # Mock download failure
    def mock_failed_download(url, destination, **kwargs):
        return DownloadResult(url=url, destination=Path(destination), success=False, error_message="Network timeout")

    mgr.engine.download = mock_failed_download

    summary = mgr.sync_items(["xkcd_complete_comics"], force_update=True)
    assert summary.failed == 1

    # Old working version must be preserved!
    assert old_canonical.exists()
    assert old_canonical.read_text() == "working v1 content"


def test_sync_unpacks_zip_archive_with_index_entrypoint(tmp_path):
    import zipfile
    vault_dir = tmp_path / "vault"
    config = VaultConfig(vault_dir=str(vault_dir))
    item = ResourceItem(
        id="cyberchef_suite",
        name="CyberChef Test",
        category="tools",
        language="en",
        format="zip",
        size_mb=75,
        upstream_url="https://example.org/cyberchef.zip",
    )
    catalog = ResourceCatalog([item])
    mgr = SyncManager(config, catalog)

    # Mock download creating a valid zip with CyberChef_v11.html
    def mock_zip_download(url, destination, **kwargs):
        dest_path = Path(destination)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dest_path, "w") as z:
            z.writestr("CyberChef_v11.4.0.html", "<html>CyberChef App</html>")
            z.writestr("assets/style.css", "body { color: black; }")
        return DownloadResult(url=url, destination=dest_path, success=True, bytes_downloaded=100)

    mgr.engine.download = mock_zip_download

    summary = mgr.sync_items(["cyberchef_suite"], force_update=True)
    assert summary.completed == 1

    extract_dir = vault_dir / "tools" / "cyberchef_suite"
    assert extract_dir.is_dir()
    assert (extract_dir / "index.html").exists()
    assert (extract_dir / "assets" / "style.css").exists()

