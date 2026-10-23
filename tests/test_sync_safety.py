"""Regression and acceptance tests for US8.1: safe sync (pruning, extraction, validation, manifest)."""

import hashlib
import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from offline_vault.catalog import ResourceCatalog, ResourceItem, load_catalog
from offline_vault.config import VaultConfig
from offline_vault.downloader import DownloadResult
from offline_vault.resolver import ResolvedSource
from offline_vault.sync import SyncManager, extract_archive

ZIM_BYTES = b"ZIM\x04" + b"\x00" * 60
HTML_BYTES = b"<!DOCTYPE html><html><body>Not Found</body></html>"


class StaticResolver:
    """Resolver stub returning the catalog URL (or a per-id override)."""

    def __init__(self, overrides=None):
        self.overrides = overrides or {}

    def resolve(self, item):
        return self.overrides.get(item.id, ResolvedSource(url=item.upstream_url))


def _zim_item(item_id, **kw):
    data = dict(id=item_id, name=item_id, category="wiki", language="en", format="zim", size_mb=1,
                upstream_url=f"https://example.org/{item_id}.zim")
    data.update(kw)
    return ResourceItem(**data)


def _writer(payload):
    def fake_download(url, destination, **kwargs):
        dest = Path(destination)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(payload(url) if callable(payload) else payload)
        return DownloadResult(url=url, destination=dest, success=True, bytes_downloaded=dest.stat().st_size)
    return fake_download


def _manager(tmp_path, items, resolver=None):
    mgr = SyncManager(VaultConfig(vault_dir=str(tmp_path / "vault"), enable_kiwix_indexing=False),
                      ResourceCatalog(items), resolver=resolver or StaticResolver())
    return mgr


def test_syncing_one_item_never_deletes_other_items(tmp_path):
    catalog = load_catalog()
    wiki = [i for i in catalog.items if i.category == "wiki"]
    mgr = SyncManager(VaultConfig(vault_dir=str(tmp_path), enable_kiwix_indexing=False), catalog,
                      resolver=StaticResolver())
    mgr.engine.download = _writer(ZIM_BYTES)
    summary = mgr.sync_items([i.id for i in wiki], force_update=True)
    assert summary.completed == len(wiki)
    for item in wiki:
        assert mgr.get_destination_for_item(item).exists(), f"{item.id} was deleted by a later item"


def test_unrelated_files_in_category_survive_update(tmp_path):
    item = _zim_item("wikipedia_es_top", tags=["wiki", "wikipedia"])
    mgr = _manager(tmp_path, [item])
    foreign = mgr.vault_root / "wiki" / "wikipedia_fr_manual_copy.zim"
    foreign.write_bytes(ZIM_BYTES)
    mgr.engine.download = _writer(ZIM_BYTES)
    assert mgr.sync_items([item.id], force_update=True).completed == 1
    assert foreign.exists()


def test_html_error_page_is_rejected(tmp_path):
    item = _zim_item("wikipedia_en_top")
    mgr = _manager(tmp_path, [item])
    mgr.engine.download = _writer(HTML_BYTES)
    summary = mgr.sync_items([item.id])
    assert summary.failed == 1
    assert "signature" in summary.errors[item.id].lower()
    assert not mgr.get_destination_for_item(item).exists()


def test_sha256_mismatch_is_rejected_and_old_version_kept(tmp_path):
    item = _zim_item("wikipedia_en_top")
    mgr = _manager(tmp_path, [item], StaticResolver({item.id: ResolvedSource(item.upstream_url, sha256="0" * 64)}))
    dest = mgr.get_destination_for_item(item)
    dest.write_bytes(ZIM_BYTES + b"old")
    mgr.engine.download = _writer(ZIM_BYTES + b"new")
    summary = mgr.sync_items([item.id], force_update=True)
    assert summary.failed == 1
    assert "sha-256" in summary.errors[item.id].lower()
    assert dest.read_bytes() == ZIM_BYTES + b"old"


def test_sha256_match_is_accepted(tmp_path):
    item = _zim_item("wikipedia_en_top")
    digest = hashlib.sha256(ZIM_BYTES).hexdigest()
    mgr = _manager(tmp_path, [item], StaticResolver({item.id: ResolvedSource(item.upstream_url, sha256=digest)}))
    mgr.engine.download = _writer(ZIM_BYTES)
    assert mgr.sync_items([item.id]).completed == 1


def test_current_item_is_skipped_and_changed_upstream_is_updated(tmp_path):
    item = _zim_item("wikipedia_en_top")
    resolver = StaticResolver()
    mgr = _manager(tmp_path, [item], resolver)
    calls = []

    def counting(url, destination, **kw):
        calls.append(url)
        return _writer(ZIM_BYTES)(url, destination)

    mgr.engine.download = counting
    assert mgr.sync_items([item.id]).completed == 1
    assert mgr.sync_items([item.id]).skipped == 1
    assert len(calls) == 1

    resolver.overrides[item.id] = ResolvedSource("https://example.org/wikipedia_en_top_2026-11.zim")
    assert mgr.sync_items([item.id]).completed == 1
    assert calls[-1].endswith("2026-11.zim")


def test_legacy_invalid_file_is_redownloaded(tmp_path):
    item = _zim_item("wikipedia_en_top")
    mgr = _manager(tmp_path, [item])
    dest = mgr.get_destination_for_item(item)
    dest.write_bytes(HTML_BYTES)  # garbage left by the old engine, no manifest record
    mgr.engine.download = _writer(ZIM_BYTES)
    assert mgr.sync_items([item.id]).completed == 1
    assert dest.read_bytes() == ZIM_BYTES


def test_one_failing_item_does_not_abort_batch(tmp_path):
    bad = ResourceItem(id="broken_tool", name="b", category="tools", language="en", format="zip", size_mb=1,
                       upstream_url="https://example.org/broken.zip", entrypoint="index.html")
    good = _zim_item("wikipedia_en_top")
    mgr = _manager(tmp_path, [bad, good])
    mgr.engine.download = _writer(lambda url: b"PK\x03\x04 corrupt" if url.endswith(".zip") else ZIM_BYTES)
    summary = mgr.sync_items([bad.id, good.id])
    assert summary.failed == 1 and summary.completed == 1
    assert bad.id in summary.errors


def _tar_bytes(members):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for info, data in members:
            tar.addfile(info, io.BytesIO(data) if data is not None else None)
    return buf.getvalue()


def _file(name, data=b"x"):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    return info, data


def test_tar_symlink_cannot_escape_extract_dir(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tarfile.TarInfo("link")
    link.type = tarfile.SYMTYPE
    link.linkname = str(outside)
    archive = tmp_path / "evil.tar"
    archive.write_bytes(_tar_bytes([(link, None), _file("link/evil.txt", b"pwned"), _file("index.html")]))
    dest = tmp_path / "dest"
    extract_archive(archive, dest, "tar")
    assert not (outside / "evil.txt").exists()
    assert not (dest / "link").is_symlink()
    assert (dest / "index.html").is_file()


def test_tar_traversal_and_absolute_members_skipped(tmp_path):
    archive = tmp_path / "evil.tar"
    archive.write_bytes(_tar_bytes([_file("../escape.txt"), _file("/abs.txt"), _file("ok/file.txt")]))
    dest = tmp_path / "dest"
    extract_archive(archive, dest, "tar")
    assert not (tmp_path / "escape.txt").exists()
    assert (dest / "ok" / "file.txt").is_file()
    assert not any(p.name == "abs.txt" for p in dest.rglob("*"))


def test_extract_subdir_strips_prefix_and_ignores_rest(tmp_path):
    archive = tmp_path / "bundle.tar"
    archive.write_bytes(_tar_bytes([
        _file("circuitjs1/circuitjs1", b"ELF binary"),
        _file("circuitjs1/resources/app/war/circuitjs.html", b"<html>sim</html>"),
        _file("circuitjs1/resources/app/war/circuitjs1/app.js", b"js"),
    ]))
    dest = tmp_path / "dest"
    extract_archive(archive, dest, "tar", subdir="circuitjs1/resources/app/war")
    assert (dest / "circuitjs.html").read_bytes() == b"<html>sim</html>"
    assert (dest / "circuitjs1" / "app.js").is_file()
    assert not (dest / "circuitjs1" / "circuitjs1").exists()


def test_zip_extraction_skips_macos_junk_and_traversal(tmp_path):
    archive = tmp_path / "app.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("dist/index.html", "<html>app</html>")
        z.writestr("__MACOSX/dist/._index.html", "junk")
        z.writestr("../evil.txt", "pwned")
    dest = tmp_path / "dest"
    extract_archive(archive, dest, "zip", subdir="dist")
    assert (dest / "index.html").is_file()
    assert not (tmp_path / "evil.txt").exists()
    assert not (dest / "__MACOSX").exists()


def test_tool_install_writes_redirect_to_entrypoint_and_removes_archive(tmp_path):
    item = ResourceItem(id="cyberchef_suite", name="CyberChef", category="tools", language="en", format="zip",
                        size_mb=1, upstream_url="https://example.org/cc.zip", entrypoint="CyberChef_v11.html")

    def make_zip(url):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("CyberChef_v11.html", "<html>CyberChef</html>")
            z.writestr("assets/main.js", "js")
        return buf.getvalue()

    mgr = _manager(tmp_path, [item])
    mgr.engine.download = _writer(make_zip)
    assert mgr.sync_items([item.id]).completed == 1
    app_dir = mgr.get_destination_for_item(item)
    assert app_dir == mgr.vault_root / "tools" / "cyberchef_suite"
    redirect = (app_dir / "index.html").read_text()
    assert 'url=CyberChef_v11.html' in redirect
    assert (app_dir / "assets" / "main.js").is_file()
    assert not list((mgr.vault_root / "tools").glob("*.zip"))
    assert not list((mgr.vault_root / ".tmp").glob("cyberchef_suite*"))


def test_tool_with_missing_entrypoint_fails_and_keeps_previous_install(tmp_path):
    item = ResourceItem(id="drawio_offline_suite", name="draw.io", category="tools", language="en", format="zip",
                        size_mb=1, upstream_url="https://example.org/draw.war", entrypoint="index.html")
    mgr = _manager(tmp_path, [item])
    app_dir = mgr.get_destination_for_item(item)
    app_dir.mkdir(parents=True)
    (app_dir / "index.html").write_text("previous")

    def zip_without_entry(url):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("other.html", "x")
        return buf.getvalue()

    mgr.engine.download = _writer(zip_without_entry)
    summary = mgr.sync_items([item.id], force_update=True)
    assert summary.failed == 1
    assert "entrypoint" in summary.errors[item.id]
    assert (app_dir / "index.html").read_text() == "previous"


def test_signed_url_change_with_same_checksum_is_skipped(tmp_path):
    """Docker CDN URLs are signed per request; the layer digest identifies the content."""
    item = _zim_item("excalidraw_like")
    digest = hashlib.sha256(ZIM_BYTES).hexdigest()
    resolver = StaticResolver({item.id: ResolvedSource("https://cdn.example/blob?sig=1", sha256=digest)})
    mgr = _manager(tmp_path, [item], resolver)
    mgr.engine.download = _writer(ZIM_BYTES)
    assert mgr.sync_items([item.id]).completed == 1
    resolver.overrides[item.id] = ResolvedSource("https://cdn.example/blob?sig=2", sha256=digest)
    assert mgr.sync_items([item.id]).skipped == 1
