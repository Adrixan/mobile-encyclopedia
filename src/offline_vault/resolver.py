"""Upstream resolution: latest Kiwix books, latest GitHub release assets, and direct URLs."""

from __future__ import annotations

import os
import re
import threading
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests

from offline_vault.catalog import ResourceItem

KIWIX_LIBRARY_URL = "https://download.kiwix.org/library/library_zim.xml"
GITHUB_LATEST_RELEASE_URL = "https://api.github.com/repos/{repo}/releases/latest"
DOCKER_AUTH_URL = "https://auth.docker.io/token?service=registry.docker.io&scope=repository:{image}:pull"
DOCKER_REGISTRY_URL = "https://registry-1.docker.io/v2/{image}"
FDROID_PACKAGE_API = "https://f-droid.org/api/v1/packages/{package}"
FDROID_APK_URL = "https://f-droid.org/repo/{package}_{version_code}.apk"
OCI_MANIFEST_TYPES = ", ".join([
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
])
# Python's tarfile reads gzip; zstd layers would need Python 3.14
OCI_GZIP_LAYER_TYPES = {
    "application/vnd.oci.image.layer.v1.tar+gzip",
    "application/vnd.docker.image.rootfs.diff.tar.gzip",
}
USER_AGENT = "OfflineVault/0.2"
LIBRARY_CACHE_FILE = "kiwix_library_zim.xml"
LIBRARY_MAX_AGE_SEC = 24 * 3600

_SHA256_RE = re.compile(r"^([0-9a-fA-F]{64})\b")


@dataclass(frozen=True)
class ResolvedSource:
    """Concrete download location for a catalog item."""

    url: str
    sha256: Optional[str] = None
    size_bytes: Optional[int] = None
    # Upstream validator (ETag, or Last-Modified plus length) for URLs that never change name
    version: Optional[str] = None


@dataclass(frozen=True)
class KiwixBook:
    """Latest known release of a Kiwix book (name + flavour)."""

    name: str
    flavour: str
    date: str
    url: str
    size_bytes: Optional[int]


def get_cache_dir() -> Path:
    """Return the per-user cache directory (XDG_CACHE_HOME or ~/.cache)."""
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "offline-vault"


def _is_https(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def parse_kiwix_library(xml_bytes: bytes) -> Dict[Tuple[str, str], KiwixBook]:
    """Parse Kiwix library_zim.xml and keep the newest book per (name, flavour)."""
    root = ET.fromstring(xml_bytes)
    latest: Dict[Tuple[str, str], KiwixBook] = {}
    for book in root.iter("book"):
        attrs = book.attrib
        name = attrs.get("name", "")
        url = attrs.get("url", "")
        if url.endswith(".meta4"):
            url = url[: -len(".meta4")]
        if not name or not url.endswith(".zim") or not _is_https(url):
            continue
        size_kb = attrs.get("size", "")
        candidate = KiwixBook(
            name=name,
            flavour=attrs.get("flavour", ""),
            date=attrs.get("date", ""),
            url=url,
            size_bytes=int(size_kb) * 1024 if size_kb.isdigit() else None,
        )
        key = (candidate.name, candidate.flavour)
        current = latest.get(key)
        if current is None or (candidate.date, candidate.url) > (current.date, current.url):
            latest[key] = candidate
    return latest


def parse_sha256_sidecar(text: str) -> Optional[str]:
    """Extract the hex digest from a `sha256sum`-style sidecar file."""
    match = _SHA256_RE.match(text.strip())
    return match.group(1).lower() if match else None


class Resolver:
    """Resolves catalog items to concrete, verifiable download locations."""

    def __init__(
        self,
        session: Optional[Any] = None,
        cache_dir: Optional[Path] = None,
        library_max_age: int = LIBRARY_MAX_AGE_SEC,
        timeout: int = 30,
    ) -> None:
        self.session = session or requests.Session()
        self.cache_dir = Path(cache_dir) if cache_dir else get_cache_dir()
        self.library_max_age = library_max_age
        self.timeout = timeout
        self._books: Optional[Dict[Tuple[str, str], KiwixBook]] = None
        self._books_lock = threading.Lock()

    def _get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        allow_redirects: bool = True,
        stream: bool = False,
    ) -> Any:
        merged = {"User-Agent": USER_AGENT, **(headers or {})}
        kwargs: Dict[str, Any] = {"headers": merged, "timeout": self.timeout, "allow_redirects": allow_redirects}
        if stream:
            kwargs["stream"] = True
        return self.session.get(url, **kwargs)

    def kiwix_books(self) -> Dict[Tuple[str, str], KiwixBook]:
        """Return the Kiwix library index, using a disk cache to spare mobile data."""
        with self._books_lock:
            return self._load_kiwix_books()

    def _load_kiwix_books(self) -> Dict[Tuple[str, str], KiwixBook]:
        if self._books is not None:
            return self._books

        cache_file = self.cache_dir / LIBRARY_CACHE_FILE
        cache_fresh = cache_file.is_file() and (time.time() - cache_file.stat().st_mtime) < self.library_max_age
        data: Optional[bytes] = cache_file.read_bytes() if cache_fresh else None

        if data is None:
            try:
                resp = self._get(KIWIX_LIBRARY_URL)
                if resp.status_code == 200 and resp.content:
                    data = resp.content
                    self.cache_dir.mkdir(parents=True, exist_ok=True)
                    tmp = cache_file.with_suffix(".tmp")
                    tmp.write_bytes(data)
                    tmp.replace(cache_file)
            except (requests.RequestException, OSError):
                data = None
            if data is None and cache_file.is_file():
                # Offline: a stale index is better than none
                data = cache_file.read_bytes()

        try:
            self._books = parse_kiwix_library(data) if data else {}
        except ET.ParseError:
            self._books = {}
        return self._books

    def _kiwix_sha256(self, url: str) -> Optional[str]:
        try:
            resp = self._get(url + ".sha256")
            if resp.status_code == 200:
                return parse_sha256_sidecar(resp.text)
        except requests.RequestException:
            pass
        return None

    def _resolve_kiwix(self, item: ResourceItem) -> ResolvedSource:
        book = self.kiwix_books().get((item.kiwix_name, item.kiwix_flavour))
        if book is None:
            return ResolvedSource(url=item.upstream_url)
        return ResolvedSource(url=book.url, sha256=self._kiwix_sha256(book.url), size_bytes=book.size_bytes)

    def _resolve_github(self, item: ResourceItem) -> ResolvedSource:
        pattern = re.compile(item.asset_pattern)
        # Optional token lifts the anonymous API limit (60 requests/hour) that drops asset digests
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        auth = {"Authorization": f"Bearer {token}"} if token else None
        try:
            resp = self._get(GITHUB_LATEST_RELEASE_URL.format(repo=item.github_repo), auth)
            if resp.status_code != 200:
                return ResolvedSource(url=item.upstream_url)
            for asset in resp.json().get("assets", []):
                name = str(asset.get("name", ""))
                url = str(asset.get("browser_download_url", ""))
                if not pattern.fullmatch(name) or not _is_https(url):
                    continue
                digest = str(asset.get("digest") or "")
                sha = digest.split(":", 1)[1].lower() if digest.startswith("sha256:") else None
                size = asset.get("size")
                return ResolvedSource(url=url, sha256=sha, size_bytes=int(size) if isinstance(size, int) else None)
        except (requests.RequestException, ValueError, AttributeError):
            pass
        return ResolvedSource(url=item.upstream_url)

    def _resolve_oci(self, item: ResourceItem) -> ResolvedSource:
        """Top filesystem layer of a Docker Hub image (where a final COPY puts a built web app)."""
        try:
            token = self._get(DOCKER_AUTH_URL.format(image=item.oci_image)).json()["token"]
            auth = {"Authorization": f"Bearer {token}"}
            registry = DOCKER_REGISTRY_URL.format(image=item.oci_image)
            manifest = self._get(f"{registry}/manifests/{item.oci_tag}", {**auth, "Accept": OCI_MANIFEST_TYPES}).json()
            if "manifests" in manifest:
                # Static web files are architecture independent; prefer linux/amd64 for a stable choice
                platforms = [m for m in manifest["manifests"] if m.get("platform", {}).get("os") == "linux"]
                chosen = next((m for m in platforms if m["platform"].get("architecture") == "amd64"), None)
                chosen = chosen or (platforms[0] if platforms else None)
                if chosen is None:
                    return ResolvedSource(url=item.upstream_url)
                manifest = self._get(f"{registry}/manifests/{chosen['digest']}",
                                     {**auth, "Accept": OCI_MANIFEST_TYPES}).json()
            layer = manifest["layers"][-1]
            digest = str(layer["digest"])
            if layer.get("mediaType") not in OCI_GZIP_LAYER_TYPES or not digest.startswith("sha256:"):
                return ResolvedSource(url=item.upstream_url)
            blob = self._get(f"{registry}/blobs/{digest}", auth, allow_redirects=False)
            location = blob.headers.get("Location", "") if blob.status_code in (301, 302, 303, 307, 308) else ""
            if not _is_https(location):
                return ResolvedSource(url=item.upstream_url)
            return ResolvedSource(url=location, sha256=digest.split(":", 1)[1], size_bytes=int(layer.get("size") or 0) or None)
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError, AttributeError):
            return ResolvedSource(url=item.upstream_url)

    def _resolve_fdroid(self, item: ResourceItem) -> ResolvedSource:
        """F-Droid's suggested (stable) APK; Android verifies the APK signature on install."""
        try:
            data = self._get(FDROID_PACKAGE_API.format(package=item.fdroid_package)).json()
            code = int(data["suggestedVersionCode"])
            if any(int(p.get("versionCode", -1)) == code for p in data.get("packages", [])):
                return ResolvedSource(url=FDROID_APK_URL.format(package=item.fdroid_package, version_code=code))
        except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError):
            pass
        return ResolvedSource(url=item.upstream_url)

    @staticmethod
    def _version_from_headers(headers: Any) -> Optional[str]:
        etag = headers.get("ETag")
        total = headers.get("Content-Range", "").rpartition("/")[2] or headers.get("Content-Length", "")
        last_modified = headers.get("Last-Modified")
        return etag or (f"{last_modified}|{total}" if last_modified else None)

    def _resolve_url(self, item: ResourceItem) -> ResolvedSource:
        """Fixed URL: read its validator with HEAD, else a one-byte ranged GET (some servers ignore HEAD).

        HEAD first keeps load low on hosts that rate-limit downloads (each sync probes once per item).
        """
        head = getattr(self.session, "head", None)
        if head is not None:
            try:
                resp = head(item.upstream_url, headers={"User-Agent": USER_AGENT}, timeout=15, allow_redirects=True)
                if resp.status_code == 200:
                    version = self._version_from_headers(resp.headers)
                    if version:
                        return ResolvedSource(url=item.upstream_url, version=version)
            except requests.RequestException:
                pass
        try:
            resp = self._get(item.upstream_url, {"Range": "bytes=0-0"}, stream=True)
            try:
                if resp.status_code not in (200, 206):
                    return ResolvedSource(url=item.upstream_url)
                return ResolvedSource(url=item.upstream_url, version=self._version_from_headers(resp.headers))
            finally:
                close = getattr(resp, "close", None)
                if close:
                    close()
        except requests.RequestException:
            return ResolvedSource(url=item.upstream_url)

    def _resolve_index(self, item: ResourceItem) -> ResolvedSource:
        """Newest file in an HTML directory listing whose name matches the pattern."""
        pattern = re.compile(item.index_pattern)
        try:
            resp = self._get(item.index_url)
            if resp.status_code != 200:
                return ResolvedSource(url=item.upstream_url)
            names = {href.rsplit("/", 1)[-1] for href in re.findall(r'href="([^"?#]+)"', resp.text)}
            matches = [n for n in names if pattern.fullmatch(n)]
        except requests.RequestException:
            return ResolvedSource(url=item.upstream_url)
        if not matches:
            return ResolvedSource(url=item.upstream_url)

        def natural_key(name: str) -> List[Any]:
            return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", name)]

        url = urljoin(item.index_url, max(matches, key=natural_key))
        return ResolvedSource(url=url) if _is_https(url) else ResolvedSource(url=item.upstream_url)

    def resolve(self, item: ResourceItem) -> ResolvedSource:
        """Resolve an item to the newest download; falls back to the catalog URL."""
        if item.source == "kiwix":
            return self._resolve_kiwix(item)
        if item.source == "github":
            return self._resolve_github(item)
        if item.source == "oci":
            return self._resolve_oci(item)
        if item.source == "fdroid":
            return self._resolve_fdroid(item)
        if item.source == "index":
            return self._resolve_index(item)
        if item.source == "url":
            return self._resolve_url(item)
        return ResolvedSource(url=item.upstream_url)
