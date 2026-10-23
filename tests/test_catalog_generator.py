"""Tests for scripts/generate_catalog.py and the tracked catalog spec (offline, no network)."""

import importlib.util
from pathlib import Path

import pytest
import yaml

from offline_vault.catalog import load_catalog
from offline_vault.resolver import KiwixBook, ResolvedSource

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "scripts" / "catalog_spec.yaml"


def _load_generator():
    spec = importlib.util.spec_from_file_location("generate_catalog", ROOT / "scripts" / "generate_catalog.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeLookups:
    """Stand-in for live upstream lookups."""

    def __init__(self):
        self.books = {("wikipedia_de_top", "nopic"): KiwixBook(
            "wikipedia_de_top", "nopic", "2026-10-10",
            "https://download.kiwix.org/zim/wikipedia/wikipedia_de_top_nopic_2026-10.zim", 1219 * 1048576)}
        self.channels = {"3e464ee12f6a50a781cddf59147b48b1": {"published_size": 15 * 1048576}}

    def github_asset(self, repo, pattern):
        return ResolvedSource(f"https://github.com/{repo}/releases/download/v1/app.apk", size_bytes=3 * 1048576)

    def resolve(self, item):
        return ResolvedSource("https://cdn.example/layer?sig=1", sha256="a" * 64, size_bytes=2 * 1048576)

    def url_size(self, url):
        return 5 * 1048576


def test_generator_renders_a_valid_catalog_offline(tmp_path):
    gen = _load_generator()
    spec = {
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
            {"id": "periodic", "name": "P", "source": "url", "format": "tar", "url": "https://example.org/p.tgz",
             "entrypoint": "index.html", "size_mb": 1, "description": "d", "tags": []},
        ],
        "apps": [{"id": "trail_sense_apk", "name": "Trail Sense", "source": "github", "format": "apk",
                  "github_repo": "kylecorry31/Trail-Sense", "asset_pattern": r"Trail-Sense-.*\.apk",
                  "description": "d", "tags": []}],
    }
    out = tmp_path / "catalog.yaml"
    out.write_text(gen.render_catalog(spec, FakeLookups()), encoding="utf-8")
    catalog = load_catalog(out)
    assert {i.id for i in catalog.items} == {"wikipedia_de_top", "sikana_en", "excalidraw_whiteboard", "periodic",
                                             "trail_sense_apk"}
    wiki = catalog.get_by_id("wikipedia_de_top")
    assert wiki.size_mb == 1219 and wiki.upstream_url.endswith("nopic_2026-10.zim") and "starter" in wiki.tags
    assert catalog.get_by_id("sikana_en").size_mb == 15
    oci = catalog.get_by_id("excalidraw_whiteboard")
    assert oci.upstream_url == "https://hub.docker.com/r/excalidraw/excalidraw" and oci.size_mb == 2
    assert oci.serve_root and oci.patches == [{"file": "index.html", "pattern": "x", "replace": ""}]
    assert catalog.get_by_id("periodic").size_mb == 1
    assert catalog.get_by_id("trail_sense_apk").size_mb == 3


def test_generator_fails_loudly_on_missing_upstream():
    gen = _load_generator()
    with pytest.raises(gen.GenerationError, match="kiwix book"):
        gen.render_catalog({"wiki": [{"id": "gone", "name": "g", "source": "kiwix", "kiwix_name": "removed",
                                      "description": "d", "tags": []}]}, FakeLookups())
    with pytest.raises(gen.GenerationError, match="starter"):
        gen.render_catalog({"starter": "unknown_id", "wiki": []}, FakeLookups())


def test_tracked_spec_matches_generated_catalog():
    """The committed catalog must be generated from the committed spec."""
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    starter = set(spec.pop("starter", "").split())
    catalog = load_catalog()
    spec_items = {e["id"]: (category, e) for category, entries in spec.items() for e in entries}
    assert set(spec_items) == {i.id for i in catalog.items}
    for item in catalog.items:
        category, entry = spec_items[item.id]
        assert item.category == category, item.id
        assert item.source == entry["source"], item.id
        assert item.name == entry["name"], item.id
        assert item.description == entry["description"], item.id
        assert item.patches == entry.get("patches", []), item.id
        assert item.entrypoint == entry.get("entrypoint", ""), item.id
        assert ("starter" in item.tags) == (item.id in starter), item.id
