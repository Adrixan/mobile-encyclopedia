"""Build the resource catalog from the packaged spec with live upstream data.

Fills ``upstream_url`` and ``size_mb`` for every spec entry (latest Kiwix book, GitHub release asset,
Docker image layer, F-Droid APK, Kolibri channel, newest file in a directory listing or a fixed URL)
and tags the phone starter set.

Two modes:
- tolerant (``offline-vault refresh``): entries that cannot be resolved keep their packaged values and
  the result goes to the per-user catalog, so the app updates its own index without maintainer tools;
- strict (``scripts/generate_catalog.py``): any unresolved entry aborts, used to regenerate the
  packaged catalog.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, TextIO, Tuple

import requests
import yaml

from offline_vault.catalog import (
    ResourceItem,
    get_default_catalog_file,
    get_spec_file,
    get_user_catalog_file,
    load_catalog,
    spec_digest,
    validate_resource_item,
)
from offline_vault.resolver import KiwixBook, ResolvedSource, Resolver, get_cache_dir

KOLIBRI_CHANNELS_URL = "https://studio.learningequality.org/api/public/v1/channels"
KOLIBRI_CHANNELS_FILE = "kolibri_channels.json"
INPUT_MAX_AGE_SEC = 24 * 3600
# Some hosts (e.g. the IF Archive) only answer browser-like clients
BROWSER_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0"}

CATEGORY_TITLES = {
    "admin": "Distro & System Administration",
    "dev": "Programming, Web & DevOps References (DevDocs ZIMs)",
    "tutorials": "Courses & Interactive Learning",
    "wiki": "Multilingual Encyclopedias & Dictionaries",
    "survival": "Survival, Health, Repair & Engineering",
    "maps": "Offline Maps",
    "qna": "Q&A Archives",
    "fun": "Books, Comics & Interactive Fiction",
    "tools": "Prebuilt Offline Web Apps",
    "apps": "Android Apps (APKs to install offline)",
}
FIELD_ORDER = [
    "id", "name", "category", "language", "format", "size_mb", "source", "kiwix_name", "kiwix_flavour",
    "github_repo", "asset_pattern", "kolibri_channel", "oci_image", "oci_tag", "fdroid_package", "index_url",
    "index_pattern", "upstream_url", "extract_subdir", "entrypoint", "serve_root", "patches", "description", "tags",
]
HEADER = [
    "# Offline Knowledge Catalog: GENERATED from src/offline_vault/data/catalog_spec.yaml.",
    "# Edit the spec, not this file. Sizes in MB. Every item is usable on Android: ZIMs in Kiwix, EPUBs in",
    "# KOReader, .map in Locus Map/OruxMaps, web apps through `offline-vault serve` plus a browser,",
    "# Kolibri channels in Kolibri, APKs via the file manager.",
    "",
]


class GenerationError(RuntimeError):
    """An entry could not be resolved against its upstream source."""


@dataclass
class BuildReport:
    """Outcome of a catalog build."""

    items: int = 0
    failed: List[Tuple[str, str]] = field(default_factory=list)


class Lookups(Protocol):
    """Upstream lookups used by the builder (live in production, faked in tests)."""

    books: Dict[Tuple[str, str], KiwixBook]
    channels: Dict[str, Dict[str, Any]]

    def github_asset(self, repo: str, pattern: str) -> ResolvedSource: ...

    def resolve(self, item: ResourceItem) -> ResolvedSource: ...

    def url_size(self, url: str) -> int: ...


def size_mb(size_bytes: int) -> int:
    """Round a byte count up to whole MB (at least 1)."""
    return max(1, math.ceil(size_bytes / 1048576))


class LiveLookups:
    """Live upstream lookups; the Kiwix and Kolibri indexes are cached in the cache dir for 24 hours."""

    def __init__(self, cache_dir: Path, refresh: bool = False) -> None:
        self.session = requests.Session()
        self.resolver = Resolver(session=self.session, cache_dir=cache_dir,
                                 library_max_age=0 if refresh else INPUT_MAX_AGE_SEC)
        self.books = self.resolver.kiwix_books()
        if not self.books:
            raise GenerationError("Kiwix library index unavailable (offline?)")
        self.channels = self._kolibri_channels(Path(cache_dir) / KOLIBRI_CHANNELS_FILE, refresh)

    def _kolibri_channels(self, path: Path, refresh: bool) -> Dict[str, Dict[str, Any]]:
        fresh = path.is_file() and time.time() - path.stat().st_mtime < INPUT_MAX_AGE_SEC
        if refresh or not fresh:
            try:
                resp = self.session.get(KOLIBRI_CHANNELS_URL, timeout=60)
                resp.raise_for_status()
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(".tmp")
                tmp.write_bytes(resp.content)
                tmp.replace(path)
            except requests.RequestException:
                if not path.is_file():
                    return {}
        try:
            return {c["id"]: c for c in json.loads(path.read_text(encoding="utf-8"))}
        except (OSError, ValueError, KeyError, TypeError):
            return {}

    def github_asset(self, repo: str, pattern: str) -> ResolvedSource:
        placeholder = f"https://github.com/{repo}/releases/latest"
        item = ResourceItem(id="probe", name="probe", category="apps", language="en", format="apk", size_mb=1,
                            upstream_url=placeholder, source="github", github_repo=repo, asset_pattern=pattern)
        res = self.resolver.resolve(item)
        if res.url == placeholder:
            raise GenerationError(f"no release asset matching {pattern!r} in {repo} (GitHub API limit? set GITHUB_TOKEN)")
        return res

    def resolve(self, item: ResourceItem) -> ResolvedSource:
        return self.resolver.resolve(item)

    def url_size(self, url: str) -> int:
        resp = self.session.get(url, headers={**BROWSER_UA, "Range": "bytes=0-0"}, allow_redirects=True,
                                timeout=60, stream=True)
        with resp:
            content_range = resp.headers.get("Content-Range", "")
            if resp.status_code == 206 and "/" in content_range:
                return int(content_range.rsplit("/", 1)[1])
            content_type = resp.headers.get("Content-Type", "")
            if resp.status_code == 200 and "html" not in content_type:
                # Server ignores Range: measure the body (only small files reach this path)
                return sum(len(chunk) for chunk in resp.iter_content(65536))
            raise GenerationError(f"cannot size {url}: HTTP {resp.status_code} {content_type}")


def build_entry(raw: Dict[str, Any], category: str, starter: set, lookups: Lookups) -> Dict[str, Any]:
    """Resolve one spec entry into a complete catalog entry (raises GenerationError if impossible)."""
    entry = dict(raw)
    entry["category"] = category
    entry.setdefault("language", "en")
    if entry["id"] in starter:
        entry["tags"] = list(entry.get("tags", [])) + ["starter"]

    source = entry["source"]
    if source == "kiwix":
        entry["format"] = "zim"
        book = lookups.books.get((entry["kiwix_name"], entry.get("kiwix_flavour", "")))
        if book is None or book.size_bytes is None:
            raise GenerationError(f"missing kiwix book {entry['kiwix_name']}:{entry.get('kiwix_flavour', '')}")
        entry["upstream_url"] = book.url
        entry["size_mb"] = size_mb(book.size_bytes)
    elif source == "github":
        res = lookups.github_asset(entry["github_repo"], entry["asset_pattern"])
        entry["upstream_url"] = res.url
        if "size_mb" not in entry:
            entry["size_mb"] = size_mb(res.size_bytes or lookups.url_size(res.url))
    elif source in ("oci", "fdroid"):
        # The catalog keeps a stable landing page; the sync resolves the actual blob or APK
        landing = (f"https://hub.docker.com/r/{entry['oci_image']}" if source == "oci"
                   else f"https://f-droid.org/packages/{entry['fdroid_package']}/")
        res = lookups.resolve(validate_resource_item(dict(entry, size_mb=1, upstream_url=landing)))
        if res.url == landing:
            raise GenerationError(f"cannot resolve {source} item {entry['id']}")
        entry["upstream_url"] = landing
        if "size_mb" not in entry:
            entry["size_mb"] = size_mb(res.size_bytes or lookups.url_size(res.url))
    elif source == "index":
        res = lookups.resolve(validate_resource_item(dict(entry, size_mb=1, upstream_url=entry.pop("url"))))
        entry["upstream_url"] = res.url
        if "size_mb" not in entry:
            entry["size_mb"] = size_mb(lookups.url_size(res.url))
    elif source == "kolibri":
        channel = lookups.channels.get(entry["kolibri_channel"])
        if channel is None:
            raise GenerationError(f"unknown kolibri channel {entry['kolibri_channel']}")
        entry["upstream_url"] = f"https://studio.learningequality.org/channels/{entry['kolibri_channel']}"
        entry["size_mb"] = size_mb(int(channel["published_size"]))
    else:
        entry["upstream_url"] = entry.pop("url")
        if "size_mb" not in entry:
            entry["size_mb"] = size_mb(lookups.url_size(entry["upstream_url"]))
    entry.pop("url", None)

    # Fail here rather than at runtime: the generated entry must pass the app's own schema
    validate_resource_item(entry)
    return entry


def _fallback_entry(raw: Dict[str, Any], category: str, starter: set, known: Dict[str, Any]) -> Dict[str, Any]:
    entry = dict(raw, category=category, upstream_url=known["upstream_url"], size_mb=known["size_mb"])
    entry.setdefault("language", "en")
    entry.pop("url", None)
    if entry["source"] == "kiwix":
        entry["format"] = "zim"
    if entry["id"] in starter:
        entry["tags"] = list(entry.get("tags", [])) + ["starter"]
    validate_resource_item(entry)
    return entry


def _render_value(key: str, value: Any) -> str:
    if key == "patches":
        return json.dumps(value, ensure_ascii=False)
    if key == "tags":
        return "[" + ", ".join(json.dumps(t) for t in value) + "]"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if key in ("asset_pattern", "index_pattern"):
        # Single quotes keep regex backslashes literal in YAML
        return "'" + value.replace("'", "''") + "'"
    return json.dumps(value, ensure_ascii=False)


def render_entry(entry: Dict[str, Any]) -> List[str]:
    """Render one entry as YAML lines in a stable field order."""
    lines: List[str] = []
    for key in FIELD_ORDER:
        if key not in entry or entry[key] in ("", None):
            continue
        prefix = "  - " if not lines else "    "
        lines.append(f"{prefix}{key}: {_render_value(key, entry[key])}")
    return lines


def render_catalog(
    spec: Dict[str, Any],
    lookups: Lookups,
    spec_version: str,
    fallback: Optional[Dict[str, Dict[str, Any]]] = None,
    log: Optional[TextIO] = None,
) -> Tuple[str, BuildReport]:
    """Resolve every spec entry and render the catalog YAML.

    With ``fallback`` (id -> {"upstream_url", "size_mb"}) unresolvable entries keep those values
    and are reported; without it the first failure raises GenerationError.
    """
    spec = dict(spec)
    starter = set(str(spec.pop("starter", "")).split())
    known_ids = {e["id"] for entries in spec.values() for e in entries}
    unknown = starter - known_ids
    if unknown:
        raise GenerationError(f"unknown starter ids: {sorted(unknown)}")

    report = BuildReport()
    lines = list(HEADER) + [f'spec_digest: "{spec_version}"', "", "resources:"]
    for category, entries in spec.items():
        if category not in CATEGORY_TITLES:
            raise GenerationError(f"unknown category {category!r} in spec")
        lines += ["  # " + "-" * 74, f"  # {CATEGORY_TITLES[category]}", "  # " + "-" * 74]
        for raw in entries:
            try:
                entry = build_entry(raw, category, starter, lookups)
            except (GenerationError, requests.RequestException, ValueError) as exc:
                if fallback is None or raw["id"] not in fallback:
                    raise GenerationError(f"{raw['id']}: {exc}") from exc
                entry = _fallback_entry(raw, category, starter, fallback[raw["id"]])
                report.failed.append((raw["id"], str(exc)))
            lines.append("")
            lines += render_entry(entry)
            report.items += 1
            if log:
                print(f"{category:<10} {entry['id']:<34} {entry['size_mb']:>7} MB  {entry['upstream_url']}", file=log)
    return "\n".join(lines) + "\n", report


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def refresh_user_catalog(cache_dir: Optional[Path] = None, force: bool = False,
                         log: Optional[TextIO] = None) -> BuildReport:
    """Rebuild the per-user catalog from live upstream data (tolerant; packaged values as fallback)."""
    spec_text = get_spec_file().read_text(encoding="utf-8")
    packaged = load_catalog(get_default_catalog_file())
    fallback = {i.id: {"upstream_url": i.upstream_url, "size_mb": i.size_mb} for i in packaged.items}
    lookups = LiveLookups(Path(cache_dir) if cache_dir else get_cache_dir(), refresh=force)
    text, report = render_catalog(yaml.safe_load(spec_text), lookups, spec_digest(spec_text), fallback, log)
    _write_atomic(get_user_catalog_file(), text)
    return report


def main(argv: Optional[List[str]] = None) -> int:
    """Strict regeneration of the packaged catalog (maintainer entry point)."""
    parser = argparse.ArgumentParser(description="Regenerate the packaged catalog from the spec (strict).")
    parser.add_argument("--output", type=Path, default=get_default_catalog_file(),
                        help="catalog to write (default: %(default)s)")
    parser.add_argument("--cache-dir", type=Path, default=get_cache_dir(),
                        help="cache for the Kiwix and Kolibri indexes (default: %(default)s)")
    parser.add_argument("--refresh", action="store_true", help="re-download the indexes even if cached today")
    args = parser.parse_args(argv)

    spec_text = get_spec_file().read_text(encoding="utf-8")
    try:
        lookups = LiveLookups(args.cache_dir, refresh=args.refresh)
        text, _ = render_catalog(yaml.safe_load(spec_text), lookups, spec_digest(spec_text), log=sys.stderr)
    except (GenerationError, requests.RequestException) as exc:
        print(f"generate_catalog: {exc}", file=sys.stderr)
        return 1
    _write_atomic(args.output, text)
    print(f"wrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
