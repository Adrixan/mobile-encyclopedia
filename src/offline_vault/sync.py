"""Synchronization manager orchestrating downloads, placement, and Kiwix library indexing."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

from offline_vault.catalog import ResourceCatalog, ResourceItem
from offline_vault.config import VaultConfig, ensure_vault_structure, get_disk_space
from offline_vault.downloader import DownloaderEngine, DownloadProgress, DownloadResult


@dataclass
class SyncSummary:
    """Summary of completed sync operations."""

    total_requested: int
    completed: int
    failed: int
    skipped: int
    total_bytes: int
    errors: Dict[str, str]


class SyncManager:
    """Orchestrates downloading resources into vault structure matching TUI categories."""

    def __init__(self, config: VaultConfig, catalog: ResourceCatalog) -> None:
        self.config = config
        self.catalog = catalog
        self.vault_root = Path(config.vault_dir).resolve()
        self.subdirs = ensure_vault_structure(self.vault_root)
        self.engine = DownloaderEngine(
            prefer_aria2=config.prefer_aria2,
            split_connections=config.aria2_split_connections,
        )

    def get_destination_for_item(self, item: ResourceItem) -> Path:
        """Resolve destination file path matching the item's category folder."""
        cat_dir = self.subdirs.get(item.category, self.vault_root / item.category)
        cat_dir.mkdir(parents=True, exist_ok=True)

        url_filename = item.upstream_url.rstrip("/").split("/")[-1]
        if "." not in url_filename or url_filename in ["all", "latest", "master.tar.gz"]:
            ext = f".{item.format}"
            filename = f"{item.id}{ext}"
        else:
            filename = url_filename
        return cat_dir / filename

    def sync_items(
        self,
        item_ids: List[str] | Set[str],
        progress_callback: Optional[Callable[[ResourceItem, DownloadProgress], None]] = None,
        item_completed_callback: Optional[Callable[[ResourceItem, DownloadResult], None]] = None,
    ) -> SyncSummary:
        """Download and register selected resources into category subdirectories."""
        completed = 0
        failed = 0
        skipped = 0
        total_bytes = 0
        errors: Dict[str, str] = {}

        for item_id in item_ids:
            item = self.catalog.get_by_id(item_id)
            if not item:
                errors[item_id] = "Item not found in catalog"
                failed += 1
                continue

            dest = self.get_destination_for_item(item)
            if dest.exists() and dest.stat().st_size > 0:
                skipped += 1
                if item_completed_callback:
                    item_completed_callback(
                        item,
                        DownloadResult(
                            url=item.upstream_url,
                            destination=dest,
                            success=True,
                            bytes_downloaded=dest.stat().st_size,
                        ),
                    )
                continue

            def item_progress(p: DownloadProgress) -> None:
                if progress_callback:
                    progress_callback(item, p)

            res = self.engine.download(
                url=item.upstream_url,
                destination=dest,
                progress_callback=item_progress,
            )

            if res.success:
                completed += 1
                total_bytes += res.bytes_downloaded
                if item.format == "zim" and self.config.enable_kiwix_indexing:
                    self.register_kiwix_zim(dest)
            else:
                failed += 1
                errors[item.id] = res.error_message or "Download failed"

            if item_completed_callback:
                item_completed_callback(item, res)

        return SyncSummary(
            total_requested=len(item_ids),
            completed=completed,
            failed=failed,
            skipped=skipped,
            total_bytes=total_bytes,
            errors=errors,
        )

    def register_kiwix_zim(self, zim_path: Path) -> bool:
        """Register ZIM file in Kiwix library.xml."""
        if not shutil.which("kiwix-manage"):
            return False

        library_xml = self.vault_root / "library.xml"
        try:
            cmd = ["kiwix-manage", str(library_xml), "add", str(zim_path)]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            return res.returncode == 0
        except Exception:
            return False
