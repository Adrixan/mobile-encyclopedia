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
    def __init__(self, status_code=200, content=b"", payload=None, headers=None):
        self.status_code = status_code
        self.content = content
        self.text = content.decode() if isinstance(content, bytes) else content
        self._payload = payload
        self.headers = headers or {}

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


def test_resolve_oci_picks_top_layer_of_linux_amd64_and_follows_blob_redirect(tmp_path):
    image = "excalidraw/excalidraw"
    token_url = f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:{image}:pull"
    reg = f"https://registry-1.docker.io/v2/{image}"
    layer = "sha256:" + "b" * 64
    session = FakeSession({
        token_url: FakeResponse(payload={"token": "t0k"}),
        f"{reg}/manifests/latest": FakeResponse(payload={
            "mediaType": "application/vnd.oci.image.index.v1+json",
            "manifests": [
                {"digest": "sha256:arm", "platform": {"architecture": "arm64", "os": "linux"}},
                {"digest": "sha256:amd", "platform": {"architecture": "amd64", "os": "linux"}},
            ]}),
        f"{reg}/manifests/sha256:amd": FakeResponse(payload={"layers": [
            {"mediaType": "application/vnd.oci.image.layer.v1.tar+gzip", "digest": "sha256:" + "a" * 64, "size": 10},
            {"mediaType": "application/vnd.oci.image.layer.v1.tar+gzip", "digest": layer, "size": 2048},
        ]}),
        f"{reg}/blobs/{layer}": FakeResponse(status_code=307, headers={"Location": "https://cdn.example/blob?sig=1"}),
    })
    item = _item(category="tools", format="tar", source="oci", oci_image=image, oci_tag="latest",
                 upstream_url="https://hub.docker.com/r/excalidraw/excalidraw")
    res = Resolver(session=session, cache_dir=tmp_path).resolve(item)
    assert res.url == "https://cdn.example/blob?sig=1"
    assert res.sha256 == "b" * 64
    assert res.size_bytes == 2048


def test_resolve_oci_rejects_non_gzip_layers(tmp_path):
    image = "a/b"
    token_url = f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:{image}:pull"
    reg = f"https://registry-1.docker.io/v2/{image}"
    session = FakeSession({
        token_url: FakeResponse(payload={"token": "t"}),
        f"{reg}/manifests/latest": FakeResponse(payload={"layers": [
            {"mediaType": "application/vnd.oci.image.layer.v1.tar+zstd", "digest": "sha256:" + "c" * 64, "size": 1}]}),
    })
    item = _item(category="tools", format="tar", source="oci", oci_image=image, oci_tag="latest",
                 upstream_url="https://hub.docker.com/r/a/b")
    assert Resolver(session=session, cache_dir=tmp_path).resolve(item).url == item.upstream_url


def test_resolve_fdroid_suggested_apk(tmp_path):
    pkg = "com.google.android.stardroid"
    session = FakeSession({f"https://f-droid.org/api/v1/packages/{pkg}": FakeResponse(payload={
        "packageName": pkg, "suggestedVersionCode": 1763,
        "packages": [{"versionName": "2.1.5-beta", "versionCode": 1770}, {"versionName": "2.1.4", "versionCode": 1763}]})})
    item = _item(category="apps", format="apk", source="fdroid", fdroid_package=pkg,
                 upstream_url=f"https://f-droid.org/packages/{pkg}/")
    res = Resolver(session=session, cache_dir=tmp_path).resolve(item)
    assert res.url == f"https://f-droid.org/repo/{pkg}_1763.apk"


def test_github_token_from_environment_is_sent_only_to_api(tmp_path, monkeypatch):
    api = "https://api.github.com/repos/a/b/releases/latest"
    seen = {}

    class RecordingSession(FakeSession):
        def get(self, url, **kwargs):
            seen[url] = kwargs.get("headers", {})
            return super().get(url, **kwargs)

    payload = {"assets": [{"name": "app.zip", "browser_download_url": "https://github.com/a/b/app.zip"}]}
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    item = _item(category="tools", format="zip", source="github", github_repo="a/b",
                 asset_pattern=r"app\.zip", upstream_url="https://github.com/pinned.zip")
    Resolver(session=RecordingSession({api: FakeResponse(payload=payload)}), cache_dir=tmp_path).resolve(item)
    assert seen[api]["Authorization"] == "Bearer ghp_test"


def test_resolve_url_reports_version_from_etag_or_last_modified(tmp_path):
    url = "https://download.mapsforge.org/maps/v5/europe/austria.map"
    session = FakeSession({url: FakeResponse(headers={"ETag": '"abc-1"', "Content-Length": "554110376"})})
    res = Resolver(session=session, cache_dir=tmp_path).resolve(
        _item(category="maps", format="map", upstream_url=url))
    assert res.url == url and res.version == '"abc-1"'

    session = FakeSession({url: FakeResponse(headers={"Last-Modified": "Fri, 21 Aug 2026 12:21:09 GMT",
                                                      "Content-Length": "10"})})
    res = Resolver(session=session, cache_dir=tmp_path).resolve(_item(category="maps", format="map", upstream_url=url))
    assert res.version == "Fri, 21 Aug 2026 12:21:09 GMT|10"


def test_resolve_url_offline_has_no_version(tmp_path):
    item = _item(category="maps", format="map", upstream_url="https://example.org/a.map")
    res = Resolver(session=FakeSession({}), cache_dir=tmp_path).resolve(item)
    assert res.url == item.upstream_url and res.version is None


def test_resolve_index_picks_highest_version(tmp_path):
    index = "https://www.falstad.com/circuit/offline/"
    listing = (b'<a href="circuitjs1-5.0.1ts-linux64.tgz">a</a><a href="circuitjs1-5.10.0ts-linux64.tgz">b</a>'
               b'<a href="circuitjs1-5.2.0ts-linux64.tgz">c</a><a href="circuitjs1-5.10.0ts-win.zip">d</a>')
    session = FakeSession({index: FakeResponse(content=listing)})
    item = _item(category="tools", format="tar", source="index", index_url=index,
                 index_pattern=r"circuitjs1-[0-9.]+ts-linux64\.tgz",
                 upstream_url="https://www.falstad.com/circuit/offline/circuitjs1-5.0.1ts-linux64.tgz")
    res = Resolver(session=session, cache_dir=tmp_path).resolve(item)
    assert res.url == "https://www.falstad.com/circuit/offline/circuitjs1-5.10.0ts-linux64.tgz"


def test_resolve_url_prefers_head_and_skips_get_when_validator_found(tmp_path):
    url = "https://standardebooks.org/ebooks/x/downloads/x.epub?source=download"

    class HeadSession(FakeSession):
        def head(self, u, **kwargs):
            self.calls.append(("HEAD", u))
            return FakeResponse(headers={"ETag": '"se-1"', "Content-Length": "633860"})

    session = HeadSession({url: FakeResponse(headers={"ETag": '"from-get"'})})
    res = Resolver(session=session, cache_dir=tmp_path).resolve(_item(category="fun", format="epub", upstream_url=url))
    assert res.version == '"se-1"'
    assert session.calls == [("HEAD", url)]


def test_resolve_url_falls_back_to_ranged_get_when_head_fails(tmp_path):
    import requests

    url = "https://download.geogebra.org/package/geogebra-math-apps-bundle"

    class NoHeadSession(FakeSession):
        def head(self, u, **kwargs):
            raise requests.ConnectTimeout("HEAD ignored")

    session = NoHeadSession({url: FakeResponse(status_code=206, headers={"ETag": '"ggb"', "Content-Range": "bytes 0-0/33461640"})})
    res = Resolver(session=session, cache_dir=tmp_path).resolve(_item(category="tools", format="zip", upstream_url=url))
    assert res.version == '"ggb"'
