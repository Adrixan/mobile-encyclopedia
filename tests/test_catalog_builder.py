"""Tests for the in-app catalog builder, `offline-vault refresh` and the packaged spec (offline)."""

import pytest
import yaml

from offline_vault import catalog_builder as builder
from offline_vault.catalog import get_default_catalog_file, get_spec_file, load_catalog, spec_digest
from offline_vault.resolver import KiwixBook, ResolvedSource


class FakeLookups:
    """Stand-in for live upstream lookups."""

    def __init__(self, missing_books=()):
        self.books = {("wikipedia_de_top", "nopic"): KiwixBook(
            "wikipedia_de_top", "nopic", "2026-10-10",
            "https://download.kiwix.org/zim/wikipedia/wikipedia_de_top_nopic_2026-10.zim", 1219 * 1048576)}
        for key in missing_books:
            self.books.pop(key, None)
        self.channels = {"3e464ee12f6a50a781cddf59147b48b1": {"published_size": 15 * 1048576}}

    def github_asset(self, repo, pattern):
        return ResolvedSource(f"https://github.com/{repo}/releases/download/v1/app.apk", size_bytes=3 * 1048576)

    def resolve(self, item):
        if item.source == "index":
            return ResolvedSource("https://www.falstad.com/circuit/offline/circuitjs1-5.1.0ts-linux64.tgz")
        return ResolvedSource("https://cdn.example/layer?sig=1", sha256="a" * 64, size_bytes=2 * 1048576)

    def url_size(self, url):
        return 5 * 1048576


SPEC = {
    "starter": "wikipedia_de_top",
    "wiki": [{"id": "wikipedia_de_top", "name": "Wikipedia DE", "source": "kiwix",
              "kiwix_name": "wikipedia_de_top", "kiwix_flavour": "nopic", "language": "de",
              "description": "d", "tags": ["wiki"]}],
    "survival": [{"id": "sikana_en", "name": "Sikana", "source": "kolibri", "format": "kolibri",
                  "kolibri_channel": "3e464ee12f6a50a781cddf59147b48b1", "description": "d", "tags": []}],
    "tools": [
        {"id": "excalidraw_whiteboard", "name": "Excalidraw", "source": "oci", "format": "tar",
         "oci_image": "excalidraw/excalidraw", "oci_tag": "latest", "extract_subdir": "usr/share/nginx/html",
         "entrypoint": "index.html", "serve_root": True,
         "patches": [{"file": "index.html", "pattern": "x", "replace": ""}], "description": "d", "tags": []},
        {"id": "circuitjs_simulator", "name": "CircuitJS1", "source": "index", "format": "tar",
         "index_url": "https://www.falstad.com/circuit/offline/", "index_pattern": r"circuitjs1-[0-9.]+ts-linux64\.tgz",
         "url": "https://www.falstad.com/circuit/offline/circuitjs1-5.0.1ts-linux64.tgz",
         "entrypoint": "circuitjs.html", "description": "d", "tags": []},
        {"id": "periodic", "name": "P", "source": "url", "format": "tar", "url": "https://example.org/p.tgz",
         "entrypoint": "index.html", "size_mb": 1, "description": "d", "tags": []},
    ],
    "apps": [{"id": "trail_sense_apk", "name": "Trail Sense", "source": "github", "format": "apk",
              "github_repo": "kylecorry31/Trail-Sense", "asset_pattern": r"Trail-Sense-.*\.apk",
              "description": "d", "tags": []}],
}


def test_builder_renders_a_valid_catalog_offline(tmp_path):
    text, report = builder.render_catalog(SPEC, FakeLookups(), spec_version="abc123")
    out = tmp_path / "catalog.yaml"
    out.write_text(text, encoding="utf-8")
    catalog = load_catalog(out)
    assert yaml.safe_load(text)["spec_digest"] == "abc123"
    assert report.failed == []
    wiki = catalog.get_by_id("wikipedia_de_top")
    assert wiki.size_mb == 1219 and wiki.upstream_url.endswith("nopic_2026-10.zim") and "starter" in wiki.tags
    assert catalog.get_by_id("sikana_en").size_mb == 15
    oci = catalog.get_by_id("excalidraw_whiteboard")
    assert oci.upstream_url == "https://hub.docker.com/r/excalidraw/excalidraw" and oci.size_mb == 2
    assert oci.serve_root and oci.patches == [{"file": "index.html", "pattern": "x", "replace": ""}]
    circuit = catalog.get_by_id("circuitjs_simulator")
    assert circuit.upstream_url.endswith("circuitjs1-5.1.0ts-linux64.tgz") and circuit.size_mb == 5
    assert catalog.get_by_id("periodic").size_mb == 1
    assert catalog.get_by_id("trail_sense_apk").size_mb == 3


def test_strict_mode_fails_loudly_on_missing_upstream():
    with pytest.raises(builder.GenerationError, match="kiwix book"):
        builder.render_catalog(SPEC, FakeLookups(missing_books=[("wikipedia_de_top", "nopic")]), spec_version="x")
    with pytest.raises(builder.GenerationError, match="starter"):
        builder.render_catalog({"starter": "unknown_id", "wiki": []}, FakeLookups(), spec_version="x")


def test_tolerant_mode_keeps_packaged_values_for_unresolvable_items(tmp_path):
    fallback = {"wikipedia_de_top": {"upstream_url": "https://download.kiwix.org/zim/wikipedia/old.zim", "size_mb": 1000}}
    text, report = builder.render_catalog(SPEC, FakeLookups(missing_books=[("wikipedia_de_top", "nopic")]),
                                          spec_version="x", fallback=fallback)
    out = tmp_path / "catalog.yaml"
    out.write_text(text, encoding="utf-8")
    item = load_catalog(out).get_by_id("wikipedia_de_top")
    assert item.upstream_url.endswith("old.zim") and item.size_mb == 1000
    assert [name for name, _ in report.failed] == ["wikipedia_de_top"]


def test_load_catalog_prefers_valid_user_catalog(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    packaged = get_default_catalog_file().read_text(encoding="utf-8")
    user = tmp_path / "offline-vault" / "catalog.yaml"
    user.parent.mkdir(parents=True)
    user.write_text(packaged.replace("size_mb: 37", "size_mb: 38", 1), encoding="utf-8")
    assert load_catalog().get_by_id("archwiki_en").size_mb == 38


def test_load_catalog_ignores_user_catalog_from_other_spec_version(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    packaged = get_default_catalog_file().read_text(encoding="utf-8")
    user = tmp_path / "offline-vault" / "catalog.yaml"
    user.parent.mkdir(parents=True)
    stale = packaged.replace(spec_digest(), "0000000000000000").replace("size_mb: 37", "size_mb: 38", 1)
    user.write_text(stale, encoding="utf-8")
    assert load_catalog().get_by_id("archwiki_en").size_mb == 37
    user.write_text("resources: [broken", encoding="utf-8")
    assert load_catalog().get_by_id("archwiki_en").size_mb == 37


def test_cli_refresh_writes_user_catalog(tmp_path, monkeypatch, capsys):
    from offline_vault.cli import run_cli

    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    class AllResolvable(FakeLookups):
        def __init__(self, cache_dir, refresh=False):
            super().__init__()
            self.books = {k: KiwixBook(k[0], k[1], "2026-11-01", f"https://download.kiwix.org/zim/x/{k[0]}.zim", 42 * 1048576)
                          for k in ((e["kiwix_name"], e.get("kiwix_flavour", "")) for cat in
                                    yaml.safe_load(get_spec_file().read_text(encoding="utf-8")).values()
                                    if isinstance(cat, list) for e in cat if e["source"] == "kiwix")}
            self.channels = {c: {"published_size": 1048576} for c in (
                "1d8f6d84618153c18c695d85074952a7", "3e464ee12f6a50a781cddf59147b48b1", "131e543dbecf5776bb13cfcfddf05605")}

    monkeypatch.setattr(builder, "LiveLookups", AllResolvable)
    assert run_cli(["refresh"]) == 0
    out = capsys.readouterr().out
    assert "Catalog refreshed" in out
    assert load_catalog().get_by_id("archwiki_en").size_mb == 42


def test_packaged_catalog_matches_packaged_spec():
    """The shipped catalog must be generated from the shipped spec."""
    data = yaml.safe_load(get_default_catalog_file().read_text(encoding="utf-8"))
    assert data["spec_digest"] == spec_digest()
    spec = yaml.safe_load(get_spec_file().read_text(encoding="utf-8"))
    starter = set(spec.pop("starter", "").split())
    catalog = load_catalog(get_default_catalog_file())
    spec_items = {e["id"]: (category, e) for category, entries in spec.items() for e in entries}
    assert set(spec_items) == {i.id for i in catalog.items}
    for item in catalog.items:
        category, entry = spec_items[item.id]
        assert item.category == category, item.id
        assert item.source == entry["source"], item.id
        assert item.name == entry["name"], item.id
        assert item.patches == entry.get("patches", []), item.id
        assert ("starter" in item.tags) == (item.id in starter), item.id


def test_pinned_sizes_make_no_network_request():
    class NoSizing(FakeLookups):
        def url_size(self, url):
            raise AssertionError(f"pinned size must not be fetched: {url}")

        def github_asset(self, repo, pattern):
            return ResolvedSource(f"https://github.com/{repo}/releases/download/v1/app.apk", size_bytes=None)

    spec = {"fun": [{"id": "book", "name": "B", "source": "url", "format": "epub", "url": "https://example.org/b.epub",
                     "size_mb": 1, "description": "d", "tags": []}],
            "apps": [{"id": "app", "name": "A", "source": "github", "format": "apk", "github_repo": "a/b",
                      "asset_pattern": r"app\.apk", "size_mb": 3, "description": "d", "tags": []}]}
    text, report = builder.render_catalog(spec, NoSizing(), spec_version="x")
    assert report.failed == [] and "size_mb: 1" in text and "size_mb: 3" in text
