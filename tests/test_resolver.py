"""Tests for US8.2 upstream resolution (Kiwix library, GitHub releases, direct URLs)."""

import os
import time

from offline_vault.catalog import ResourceItem
from offline_vault.resolver import Resolver, parse_kiwix_library, parse_sha256_sidecar

LIBRARY_XML = b"""<library version="20110515">
  <book id="a" size="1000" url="https://download.kiwix.org/zim/wikipedia/wikipedia_en_top_maxi_2026-06.zim.meta4"
        name="wikipedia_en_top" flavour="maxi" date="2026-06-14"/>
  <book id="b" size="2048" url="https://download.kiwix.org/zim/wikipedia/wikipedia_en_top_maxi_2026-09.zim.meta4"
        name="wikipedia_en_top" flavour="maxi" date="2026-09-14"/>
  <book id="c" size="512" url="https://download.kiwix.org/zim/wikipedia/wikipedia_en_top_nopic_2026-10.zim.meta4"
        name="wikipedia_en_top" flavour="nopic" date="2026-10-01"/>
  <book id="d" size="64" url="https://download.kiwix.org/zim/other/gardenology.org_en_all_2026-09.zim.meta4"
        name="gardenology_en_all" date="2026-09-09"/>
</library>"""

SHA = "a" * 64


class FakeResponse:
    def __init__(self, status_code=200, content=b"", payload=None):
        self.status_code = status_code
        self.content = content
        self.text = content.decode() if isinstance(content, bytes) else content
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        return self.routes.get(url, FakeResponse(404))


def _item(**kw):
    base = dict(id="x", name="X", category="wiki", language="en", format="zim", size_mb=1,
                upstream_url="https://download.kiwix.org/zim/wikipedia/wikipedia_en_top_maxi_2026-06.zim")
    base.update(kw)
    return ResourceItem(**base)


def test_parse_kiwix_library_picks_latest_per_name_and_flavour():
    books = parse_kiwix_library(LIBRARY_XML)
    maxi = books[("wikipedia_en_top", "maxi")]
    assert maxi.url.endswith("wikipedia_en_top_maxi_2026-09.zim")
    assert maxi.size_bytes == 2048 * 1024
    assert books[("wikipedia_en_top", "nopic")].url.endswith("nopic_2026-10.zim")
    # Book names that differ from the file name resolve by name, not by URL parsing
    assert books[("gardenology_en_all", "")].url.endswith("gardenology.org_en_all_2026-09.zim")


def test_parse_sha256_sidecar():
    assert parse_sha256_sidecar(f"{SHA}  wikipedia.zim\n") == SHA
    assert parse_sha256_sidecar("<html>not found</html>") is None


def test_resolve_kiwix_item_uses_library_and_sidecar(tmp_path):
    latest = "https://download.kiwix.org/zim/wikipedia/wikipedia_en_top_maxi_2026-09.zim"
    session = FakeSession({
        "https://download.kiwix.org/library/library_zim.xml": FakeResponse(content=LIBRARY_XML),
        latest + ".sha256": FakeResponse(content=f"{SHA}  file.zim".encode()),
    })
    resolver = Resolver(session=session, cache_dir=tmp_path)
    res = resolver.resolve(_item(source="kiwix", kiwix_name="wikipedia_en_top", kiwix_flavour="maxi"))
    assert res.url == latest
    assert res.sha256 == SHA
    assert res.size_bytes == 2048 * 1024


def test_kiwix_library_is_cached_on_disk(tmp_path):
    session = FakeSession({"https://download.kiwix.org/library/library_zim.xml": FakeResponse(content=LIBRARY_XML)})
    Resolver(session=session, cache_dir=tmp_path).kiwix_books()
    second = FakeSession({})
    books = Resolver(session=second, cache_dir=tmp_path).kiwix_books()
    assert ("wikipedia_en_top", "maxi") in books
    assert second.calls == []


def test_stale_kiwix_cache_used_when_offline(tmp_path):
    session = FakeSession({"https://download.kiwix.org/library/library_zim.xml": FakeResponse(content=LIBRARY_XML)})
    Resolver(session=session, cache_dir=tmp_path).kiwix_books()
    cache_file = next(tmp_path.iterdir())
    old = time.time() - 10 * 86400
    os.utime(cache_file, (old, old))
    books = Resolver(session=FakeSession({}), cache_dir=tmp_path).kiwix_books()
    assert ("wikipedia_en_top", "maxi") in books


def test_resolve_kiwix_falls_back_to_catalog_url_when_book_missing(tmp_path):
    session = FakeSession({"https://download.kiwix.org/library/library_zim.xml": FakeResponse(content=LIBRARY_XML)})
    item = _item(source="kiwix", kiwix_name="removed_book", kiwix_flavour="")
    res = Resolver(session=session, cache_dir=tmp_path).resolve(item)
    assert res.url == item.upstream_url
    assert res.sha256 is None


def test_resolve_github_asset_with_digest(tmp_path):
    api = "https://api.github.com/repos/gchq/CyberChef/releases/latest"
    payload = {"assets": [
        {"name": "CyberChef_abc.zip.sig", "browser_download_url": "https://github.com/x/sig", "size": 1},
        {"name": "CyberChef_abc.zip", "browser_download_url": "https://github.com/x/CyberChef_abc.zip",
         "size": 4096, "digest": f"sha256:{SHA}"},
    ]}
    session = FakeSession({api: FakeResponse(payload=payload)})
    item = _item(category="tools", format="zip", source="github", github_repo="gchq/CyberChef",
                 asset_pattern=r"CyberChef_.*\.zip", upstream_url="https://github.com/pinned.zip")
    res = Resolver(session=session, cache_dir=tmp_path).resolve(item)
    assert res.url == "https://github.com/x/CyberChef_abc.zip"
    assert res.sha256 == SHA
    assert res.size_bytes == 4096


def test_resolve_github_falls_back_to_pinned_url(tmp_path):
    item = _item(category="tools", format="zip", source="github", github_repo="gchq/CyberChef",
                 asset_pattern=r"CyberChef_.*\.zip", upstream_url="https://github.com/pinned.zip")
    res = Resolver(session=FakeSession({}), cache_dir=tmp_path).resolve(item)
    assert res.url == "https://github.com/pinned.zip"


def test_resolver_rejects_non_https_results(tmp_path):
    api = "https://api.github.com/repos/a/b/releases/latest"
    payload = {"assets": [{"name": "app.zip", "browser_download_url": "http://evil.example/app.zip"}]}
    item = _item(category="tools", format="zip", source="github", github_repo="a/b",
                 asset_pattern=r"app\.zip", upstream_url="https://github.com/pinned.zip")
    res = Resolver(session=FakeSession({api: FakeResponse(payload=payload)}), cache_dir=tmp_path).resolve(item)
    assert res.url == "https://github.com/pinned.zip"
