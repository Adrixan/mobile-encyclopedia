"""Upstream resolution: latest Kiwix books, latest GitHub release assets, and direct URLs."""

from __future__ import annotations

import os
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import requests

from offline_vault.catalog import ResourceItem

KIWIX_LIBRARY_URL = "https://download.kiwix.org/library/library_zim.xml"
GITHUB_LATEST_RELEASE_URL = "https://api.github.com/repos/{repo}/releases/latest"
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

    def _get(self, url: str) -> Any:
        return self.session.get(url, headers={"User-Agent": USER_AGENT}, timeout=self.timeout)

    def kiwix_books(self) -> Dict[Tuple[str, str], KiwixBook]:
        """Return the Kiwix library index, using a disk cache to spare mobile data."""
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
        try:
            resp = self._get(GITHUB_LATEST_RELEASE_URL.format(repo=item.github_repo))
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

    def resolve(self, item: ResourceItem) -> ResolvedSource:
        """Resolve an item to the newest download; falls back to the catalog URL."""
        if item.source == "kiwix":
            return self._resolve_kiwix(item)
        if item.source == "github":
            return self._resolve_github(item)
        return ResolvedSource(url=item.upstream_url)
