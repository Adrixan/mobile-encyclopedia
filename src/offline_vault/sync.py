"""Synchronization: resolve upstream, download, verify, install atomically and record in a manifest."""

from __future__ import annotations

import html
import json
import shutil
import stat
import tarfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple

from offline_vault.catalog import ResourceCatalog, ResourceItem
from offline_vault.config import VaultConfig, ensure_vault_structure, get_disk_space
from offline_vault.downloader import (
    DownloaderEngine,
    DownloadProgress,
    DownloadResult,
    check_file_signature,
    verify_file_hash,
)
from offline_vault.kolibri import channel_database_path, import_channel
from offline_vault.resolver import ResolvedSource, Resolver

MANIFEST_DIR = ".offline-vault"
MANIFEST_FILE = "manifest.json"

REDIRECT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url={target}">
  <title>{title}</title>
</head>
<body><p><a href="{target}">Open {title}</a></p></body>
</html>
"""


@dataclass
class SyncSummary:
    """Summary of completed sync operations."""

    total_requested: int
    completed: int
    failed: int
    skipped: int
    total_bytes: int
    errors: Dict[str, str]


class Manifest:
    """Records what was installed for each item (path, source URL, checksum, size)."""

    def __init__(self, vault_root: Path) -> None:
        self.path = vault_root / MANIFEST_DIR / MANIFEST_FILE
        self.items: Dict[str, Dict[str, Any]] = {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("items"), dict):
                self.items = data["items"]
        except (OSError, ValueError):
            self.items = {}

    def get(self, item_id: str) -> Optional[Dict[str, Any]]:
        return self.items.get(item_id)

    def set(self, item_id: str, record: Dict[str, Any]) -> None:
        self.items[item_id] = record

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"version": 1, "items": self.items}, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)


def _safe_member_path(name: str, subdir: str = "") -> Optional[PurePosixPath]:
    """Map an archive member name to a safe relative path, or None if it must be skipped."""
    name = name.replace("\\", "/")
    if not name or "\x00" in name or name.startswith("/") or (len(name) > 1 and name[1] == ":"):
        return None
    parts = [p for p in name.split("/") if p not in ("", ".")]
    if ".." in parts:
        return None
    if any(p == "__MACOSX" or p.startswith("._") for p in parts):
        return None
    if subdir:
        prefix = subdir.split("/")
        if parts[: len(prefix)] != prefix:
            return None
        parts = parts[len(prefix):]
    return PurePosixPath(*parts) if parts else None


def _archive_entries(archive: Path, fmt: str) -> Iterator[Tuple[str, bool, int, Callable[[], Any]]]:
    """Yield (name, is_dir, size, opener) for regular files and dirs; links and devices are dropped."""
    if fmt == "zip":
        with zipfile.ZipFile(archive) as z:
            for info in z.infolist():
                if stat.S_ISLNK(info.external_attr >> 16):
                    continue
                yield info.filename, info.is_dir(), info.file_size, (lambda i=info: z.open(i))
    elif fmt == "tar":
        with tarfile.open(archive, "r:*") as t:
            for member in t:
                if member.isdir():
                    yield member.name, True, 0, (lambda: None)
                elif member.isfile():
                    yield member.name, False, member.size, (lambda m=member: t.extractfile(m))
    else:
        raise ValueError(f"Unsupported archive format: {fmt}")


def extract_archive(archive: Path, dest_dir: Path, fmt: str, subdir: str = "") -> int:
    """Extract only regular files and dirs below `subdir`, rejecting traversal, links and oversize content."""
    archive = Path(archive)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    root = dest_dir.resolve()

    declared = sum(size for name, is_dir, size, _ in _archive_entries(archive, fmt)
                   if not is_dir and _safe_member_path(name, subdir) is not None)
    _, _, free = get_disk_space(root)
    if declared > free:
        raise ValueError(f"Not enough disk space to extract {archive.name}: needs {declared} bytes")

    written = 0
    count = 0
    for name, is_dir, size, opener in _archive_entries(archive, fmt):
        rel = _safe_member_path(name, subdir)
        if rel is None:
            continue
        target = root.joinpath(*rel.parts)
        if not target.resolve().is_relative_to(root):
            continue
        if is_dir:
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        src = opener()
        if src is None:
            continue
        with src, open(target, "wb") as out:
            while chunk := src.read(1024 * 1024):
                written += len(chunk)
                if written > declared:
                    raise ValueError(f"Archive {archive.name} expands beyond its declared size")
                out.write(chunk)
        count += 1

    if count == 0:
        raise ValueError(f"Archive {archive.name} contained no usable files")
    return count


def _resolve_entrypoint(app_dir: Path, entrypoint: str) -> Optional[str]:
    """Return the concrete entry URL (relative to app_dir) or None if missing."""
    if entrypoint:
        path_part, sep, query = entrypoint.partition("?")
        if "*" in path_part:
            matches = sorted(p for p in app_dir.glob(path_part) if p.is_file())
            if not matches:
                return None
            path_part = matches[0].relative_to(app_dir).as_posix()
        elif not (app_dir / path_part).is_file():
            return None
        return path_part + sep + query
    if (app_dir / "index.html").is_file():
        return "index.html"
    candidates = sorted(app_dir.rglob("*.html"), key=lambda p: (len(p.relative_to(app_dir).parts), p.name != "index.html", str(p)))
    return candidates[0].relative_to(app_dir).as_posix() if candidates else None


class SyncManager:
    """Orchestrates verified downloads with canonical names, atomic installs and a manifest."""

    def __init__(
        self,
        config: VaultConfig,
        catalog: ResourceCatalog,
        resolver: Optional[Any] = None,
        create_dirs: bool = True,
    ) -> None:
        self.config = config
        self.catalog = catalog
        self.vault_root = Path(config.vault_dir).resolve()
        self.create_dirs = create_dirs
        if create_dirs:
            ensure_vault_structure(self.vault_root)
        self.tmp_dir = self.vault_root / ".tmp"
        self.resolver = resolver or Resolver()
        self.manifest = Manifest(self.vault_root)
        self.engine = DownloaderEngine(
            prefer_aria2=config.prefer_aria2,
            split_connections=config.aria2_split_connections,
        )

    def get_destination_for_item(self, item: ResourceItem) -> Path:
        """Canonical, versionless artifact path: a folder for web apps, a file otherwise."""
        if item.format == "kolibri":
            return channel_database_path(self.vault_root, item.kolibri_channel)
        cat_dir = self.vault_root / item.category
        if self.create_dirs:
            cat_dir.mkdir(parents=True, exist_ok=True)
        return cat_dir / item.id if item.is_archive else cat_dir / f"{item.id}.{item.format}"

    def artifact_exists(self, item: ResourceItem) -> bool:
        """True if the item's artifact is present and non-empty."""
        path = self.get_destination_for_item(item)
        if path.is_dir():
            return any(path.iterdir())
        return path.is_file() and path.stat().st_size > 0

    def _is_current(self, item: ResourceItem, resolved: ResolvedSource) -> bool:
        if not self.artifact_exists(item):
            return False
        record = self.manifest.get(item.id)
        if record is None:
            # Installed by an older version without a manifest: keep it if it is valid
            path = self.get_destination_for_item(item)
            return path.is_dir() or check_file_signature(path, item.format) is None
        return record.get("url") == resolved.url

    def install_archive(self, item: ResourceItem, archive: Path) -> str:
        """Extract into a staging folder, verify the entrypoint, then swap atomically. Returns the entry URL."""
        app_dir = self.get_destination_for_item(item)
        staging = app_dir.with_name(f".{item.id}.staging")
        old = app_dir.with_name(f".{item.id}.old")
        shutil.rmtree(staging, ignore_errors=True)
        try:
            extract_archive(archive, staging, item.format, item.extract_subdir)
            entry = _resolve_entrypoint(staging, item.entrypoint)
            if entry is None:
                raise ValueError(f"entrypoint '{item.entrypoint or 'index.html'}' missing from archive")
            root_index = staging / "index.html"
            if not root_index.exists():
                target = html.escape(entry, quote=True)
                root_index.write_text(REDIRECT_TEMPLATE.format(target=target, title=html.escape(item.name)),
                                      encoding="utf-8")
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise

        shutil.rmtree(old, ignore_errors=True)
        moved_old = False
        if app_dir.exists():
            app_dir.rename(old)
            moved_old = True
        try:
            staging.rename(app_dir)
        except OSError:
            if moved_old:
                old.rename(app_dir)
            shutil.rmtree(staging, ignore_errors=True)
            raise
        shutil.rmtree(old, ignore_errors=True)
        return entry

    def _sync_download(
        self,
        item: ResourceItem,
        force_update: bool,
        progress_callback: Optional[Callable[[ResourceItem, DownloadProgress], None]],
    ) -> Tuple[str, DownloadResult]:
        resolved = self.resolver.resolve(item)
        artifact = self.get_destination_for_item(item)
        if not force_update and self._is_current(item, resolved):
            return "skipped", DownloadResult(url=resolved.url, destination=artifact, success=True)

        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        staged = self.tmp_dir / f"{item.id}.{item.format}"
        partial = staged.with_name(staged.name + ".tmp")
        marker = staged.with_name(staged.name + ".src")
        # A partial from an older upstream version must not be resumed
        if marker.is_file() and marker.read_text(encoding="utf-8").strip() != resolved.url:
            partial.unlink(missing_ok=True)
            partial.with_name(partial.name + ".aria2").unlink(missing_ok=True)
        marker.write_text(resolved.url, encoding="utf-8")

        def item_progress(p: DownloadProgress) -> None:
            if progress_callback:
                progress_callback(item, p)

        res = self.engine.download(url=resolved.url, destination=staged, progress_callback=item_progress)
        if not res.success:
            return "failed", DownloadResult(url=resolved.url, destination=artifact, success=False,
                                            error_message=res.error_message or "Download failed")

        try:
            error = check_file_signature(staged, item.format)
            if error:
                raise ValueError(error)
            if resolved.sha256 and not verify_file_hash(staged, resolved.sha256):
                raise ValueError("SHA-256 checksum verification failed")
            entry = None
            if item.is_archive:
                entry = self.install_archive(item, staged)
                staged.unlink(missing_ok=True)
                # Archive file left next to the app folder by older versions (exact id only)
                (artifact.parent / f"{item.id}.{item.format}").unlink(missing_ok=True)
            else:
                staged.replace(artifact)
        finally:
            staged.unlink(missing_ok=True)
            marker.unlink(missing_ok=True)

        size = res.bytes_downloaded or 0
        self.manifest.set(item.id, {
            "path": artifact.relative_to(self.vault_root).as_posix(),
            "url": resolved.url,
            "sha256": resolved.sha256,
            "size": size,
            "entry": entry,
            "synced_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        self.manifest.save()
        return "completed", DownloadResult(url=resolved.url, destination=artifact, success=True,
                                           bytes_downloaded=size, time_taken_sec=res.time_taken_sec)

    def _sync_kolibri(self, item: ResourceItem, force_update: bool) -> Tuple[str, DownloadResult]:
        artifact = self.get_destination_for_item(item)
        if not force_update and artifact.is_file():
            return "skipped", DownloadResult(url=item.upstream_url, destination=artifact, success=True)
        ok, message = import_channel(self.vault_root, item.kolibri_channel)
        if not ok:
            return "failed", DownloadResult(url=item.upstream_url, destination=artifact, success=False,
                                            error_message=message)
        self.manifest.set(item.id, {
            "path": artifact.relative_to(self.vault_root).as_posix(),
            "url": item.upstream_url,
            "sha256": None,
            "size": None,
            "entry": None,
            "synced_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        self.manifest.save()
        return "completed", DownloadResult(url=item.upstream_url, destination=artifact, success=True)

    def sync_items(
        self,
        item_ids: List[str] | Set[str],
        force_update: bool = False,
        progress_callback: Optional[Callable[[ResourceItem, DownloadProgress], None]] = None,
        item_completed_callback: Optional[Callable[[ResourceItem, DownloadResult], None]] = None,
    ) -> SyncSummary:
        """Download missing or outdated items; one failing item never aborts the batch."""
        counts = {"completed": 0, "failed": 0, "skipped": 0}
        total_bytes = 0
        errors: Dict[str, str] = {}
        zims_changed = False

        for item_id in item_ids:
            item = self.catalog.get_by_id(item_id)
            if not item:
                errors[item_id] = "Item not found in catalog"
                counts["failed"] += 1
                continue

            try:
                if item.format == "kolibri":
                    status, result = self._sync_kolibri(item, force_update)
                else:
                    status, result = self._sync_download(item, force_update, progress_callback)
            except Exception as e:  # noqa: BLE001 - isolate per-item failures (corrupt archive, disk full)
                status = "failed"
                result = DownloadResult(url=item.upstream_url, destination=self.get_destination_for_item(item),
                                        success=False, error_message=f"{type(e).__name__}: {e}")

            counts[status] += 1
            if status == "failed":
                errors[item.id] = result.error_message or "Download failed"
            elif status == "completed":
                total_bytes += result.bytes_downloaded
                zims_changed = zims_changed or item.format == "zim"

            if item_completed_callback:
                item_completed_callback(item, result)

        if zims_changed and self.config.enable_kiwix_indexing:
            from offline_vault.server import rebuild_kiwix_library

            rebuild_kiwix_library(self.vault_root)

        return SyncSummary(
            total_requested=len(item_ids),
            completed=counts["completed"],
            failed=counts["failed"],
            skipped=counts["skipped"],
            total_bytes=total_bytes,
            errors=errors,
        )
