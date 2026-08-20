"""Synchronization manager orchestrating downloads, canonical versionless placement, and safe atomic pruning."""

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
    """Orchestrates downloading resources with canonical names and safe atomic pruning on update."""

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
        """Resolve canonical, versionless destination file path inside the category folder."""
        cat_dir = self.subdirs.get(item.category, self.vault_root / item.category)
        cat_dir.mkdir(parents=True, exist_ok=True)
        # Canonical versionless filename: <item_id>.<format>
        canonical_filename = f"{item.id}.{item.format}"
        return cat_dir / canonical_filename

    def prune_old_versions(self, item: ResourceItem, canonical_dest: Path) -> None:
        """Remove any older versions or dated files of the item in the category folder."""
        cat_dir = canonical_dest.parent
        if not cat_dir.is_dir():
            return

        keywords = {t.lower() for t in item.tags if len(t) > 2}
        for token in item.id.lower().split("_"):
            if len(token) > 2:
                keywords.add(token)

        upstream_base = item.upstream_url.split("/")[-1].split("_")[0].lower()
        if len(upstream_base) > 2:
            keywords.add(upstream_base)

        for existing_file in list(cat_dir.iterdir()):
            if existing_file.is_file() and existing_file != canonical_dest:
                name_lower = existing_file.name.lower()
                if name_lower.endswith(f".{item.format}") and any(kw in name_lower for kw in keywords):
                    try:
                        existing_file.unlink(missing_ok=True)
                    except Exception:
                        pass

    def sync_items(
        self,
        item_ids: List[str] | Set[str],
        force_update: bool = False,
        progress_callback: Optional[Callable[[ResourceItem, DownloadProgress], None]] = None,
        item_completed_callback: Optional[Callable[[ResourceItem, DownloadResult], None]] = None,
    ) -> SyncSummary:
        """Download latest versions atomically, prune old versions upon success, and register."""
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
            if dest.exists() and dest.stat().st_size > 0 and not force_update:
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

            # Atomic new download path
            new_tmp_path = dest.with_name(f"{item.id}.new.tmp")

            def item_progress(p: DownloadProgress) -> None:
                if progress_callback:
                    progress_callback(item, p)

            res = self.engine.download(
                url=item.upstream_url,
                destination=new_tmp_path,
                progress_callback=item_progress,
            )

            if res.success and new_tmp_path.exists() and new_tmp_path.stat().st_size > 0:
                # 1. Prune old/dated versions
                self.prune_old_versions(item, dest)

                # 2. Atomically replace canonical destination
                new_tmp_path.replace(dest)

                completed += 1
                total_bytes += dest.stat().st_size
                if item.format == "zim" and self.config.enable_kiwix_indexing:
                    self.register_kiwix_zim(dest)

                final_res = DownloadResult(
                    url=res.url,
                    destination=dest,
                    success=True,
                    bytes_downloaded=dest.stat().st_size,
                    time_taken_sec=res.time_taken_sec,
                )
            else:
                failed += 1
                new_tmp_path.unlink(missing_ok=True)
                errors[item.id] = res.error_message or "Download failed"
                final_res = DownloadResult(
                    url=res.url,
                    destination=dest,
                    success=False,
                    error_message=res.error_message or "Download failed",
                )

            if item_completed_callback:
                item_completed_callback(item, final_res)

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
