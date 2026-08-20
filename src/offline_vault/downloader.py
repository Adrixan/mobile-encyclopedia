"""High-throughput multi-backend resumable downloader with dynamic latest-version resolution."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import time
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import requests

_KIWIX_CACHE: Optional[Dict[str, str]] = None


def has_aria2() -> bool:
    """Check if aria2c executable is available in PATH."""
    return shutil.which("aria2c") is not None


def verify_file_hash(path: Path, expected_sha256: str) -> bool:
    """Verify SHA-256 integrity hash of a file."""
    if not path.is_file():
        return False
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().lower() == expected_sha256.lower()


def extract_kiwix_date_stamp(url_or_filename: str) -> Tuple[int, int]:
    """Extract (year, month) from Kiwix filename like name_YYYY-MM.zim."""
    match = re.search(r"_(\d{4})-(\d{2})\.zim", url_or_filename)
    if match:
        return int(match.group(1)), int(match.group(2))
    return (0, 0)


def get_kiwix_library_map() -> Dict[str, str]:
    """Fetch and parse Kiwix library XML, mapping base names to their latest live URLs."""
    global _KIWIX_CACHE
    if _KIWIX_CACHE is not None:
        return _KIWIX_CACHE

    _KIWIX_CACHE = {}
    grouped_by_base: Dict[str, List[Tuple[Tuple[int, int], str]]] = {}

    try:
        req = urllib.request.Request(
            "https://download.kiwix.org/library/library_zim.xml",
            headers={"User-Agent": "OfflineVault/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            tree = ET.parse(resp)
        root = tree.getroot()
        for b in root.findall("book"):
            url = b.attrib.get("url", "").replace(".meta4", "")
            if not url or not url.endswith(".zim"):
                continue
            fn = url.split("/")[-1]
            base = re.sub(r"_\d{4}-\d{2}\.zim$", "", fn)
            date_stamp = extract_kiwix_date_stamp(fn)

            if base not in grouped_by_base:
                grouped_by_base[base] = []
            grouped_by_base[base].append((date_stamp, url))

        # Pick the latest version for each base
        for base, versions in grouped_by_base.items():
            versions.sort(key=lambda x: x[0])
            latest_url = versions[-1][1]
            _KIWIX_CACHE[base] = latest_url
            _KIWIX_CACHE[base.replace("_maxi", "").replace("_nopic", "")] = latest_url
    except Exception:
        pass
    return _KIWIX_CACHE


def resolve_upstream_url(url: str) -> str:
    """Dynamically resolve outdated or mirror URLs to the newest active endpoint."""
    if "download.kiwix.org" in url:
        fn = url.split("/")[-1]
        base = re.sub(r"_\d{4}-\d{2}\.zim$", "", fn).replace(".zim", "")

        # Lookup in library map to find the newest dated version
        lib_map = get_kiwix_library_map()
        if base in lib_map:
            return lib_map[base]

        for k, v in lib_map.items():
            if base in k or k in base or ("explainxkcd" in base and "explainxkcd" in k):
                return v

    return url


@dataclass
class DownloadProgress:
    """Download progress update state."""

    url: str
    destination: Path
    downloaded_bytes: int
    total_bytes: Optional[int]
    speed_text: str
    percent: float


@dataclass
class DownloadResult:
    """Outcome of a download operation."""

    url: str
    destination: Path
    success: bool
    error_message: Optional[str] = None
    bytes_downloaded: int = 0
    time_taken_sec: float = 0.0


class DownloaderEngine:
    """Multi-backend download engine supporting aria2c and Python HTTP streaming."""

    def __init__(
        self,
        prefer_aria2: bool = True,
        split_connections: int = 4,
        timeout: int = 30,
    ) -> None:
        self.prefer_aria2 = prefer_aria2 and has_aria2()
        self.split_connections = split_connections
        self.timeout = timeout

    def download(
        self,
        url: str,
        destination: Path | str,
        expected_sha256: Optional[str] = None,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
    ) -> DownloadResult:
        """Download file with resume support and atomic destination renaming."""
        dest_path = Path(destination).resolve()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = dest_path.with_name(dest_path.name + ".tmp")

        start_time = time.time()
        resolved_url = resolve_upstream_url(url)

        if self.prefer_aria2 and resolved_url.startswith("https://"):
            result = self._download_aria2(resolved_url, dest_path, tmp_path, progress_callback)
            if not result.success:
                # Fallback to python streamer
                result = self._download_python(resolved_url, dest_path, tmp_path, progress_callback)
        else:
            result = self._download_python(resolved_url, dest_path, tmp_path, progress_callback)

        if result.success and expected_sha256:
            if not verify_file_hash(dest_path, expected_sha256):
                dest_path.unlink(missing_ok=True)
                return DownloadResult(
                    url=resolved_url,
                    destination=dest_path,
                    success=False,
                    error_message="Checksum verification failed",
                    time_taken_sec=time.time() - start_time,
                )

        result.time_taken_sec = time.time() - start_time
        return result

    def _download_aria2(
        self,
        url: str,
        dest_path: Path,
        tmp_path: Path,
        progress_callback: Optional[Callable[[DownloadProgress], None]],
    ) -> DownloadResult:
        """Download using aria2c with live line streaming for immediate feedback."""
        cmd = [
            "aria2c",
            "--allow-overwrite=true",
            "--auto-file-renaming=false",
            "--follow-metalink=mem",
            "--file-allocation=none",
            "--user-agent=OfflineVault/1.0",
            f"--max-connection-per-server={self.split_connections}",
            f"--split={self.split_connections}",
            "--min-split-size=1M",
            "--continue=true",
            f"--dir={tmp_path.parent}",
            f"--out={tmp_path.name}",
            "--check-certificate=true",
            "--summary-interval=1",
            url,
        ]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            progress_re = re.compile(r"([0-9.]+\w+)/([0-9.]+\w+)\((\d+)%\).*?DL:([^\s\]]+)")

            if process.stdout:
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if "%" in line:
                        match = progress_re.search(line)
                        if match and progress_callback:
                            pct = float(match.group(3))
                            speed = match.group(4)
                            progress_callback(
                                DownloadProgress(
                                    url=url,
                                    destination=dest_path,
                                    downloaded_bytes=0,
                                    total_bytes=None,
                                    speed_text=speed,
                                    percent=pct,
                                )
                            )

            process.wait()

            if process.returncode == 0 and tmp_path.exists():
                tmp_path.replace(dest_path)
                final_size = dest_path.stat().st_size
                if progress_callback:
                    progress_callback(
                        DownloadProgress(
                            url=url,
                            destination=dest_path,
                            downloaded_bytes=final_size,
                            total_bytes=final_size,
                            speed_text="Done",
                            percent=100.0,
                        )
                    )
                return DownloadResult(
                    url=url,
                    destination=dest_path,
                    success=True,
                    bytes_downloaded=final_size,
                )
            return DownloadResult(
                url=url,
                destination=dest_path,
                success=False,
                error_message=f"aria2c exited with code {process.returncode}",
            )
        except Exception as e:
            return DownloadResult(
                url=url,
                destination=dest_path,
                success=False,
                error_message=str(e),
            )

    def _download_python(
        self,
        url: str,
        dest_path: Path,
        tmp_path: Path,
        progress_callback: Optional[Callable[[DownloadProgress], None]],
    ) -> DownloadResult:
        """Download using Python requests with HTTP Range headers for resuming."""
        existing_size = tmp_path.stat().st_size if tmp_path.exists() else 0
        headers = {"User-Agent": "OfflineVault/1.0"}
        if existing_size > 0:
            headers["Range"] = f"bytes={existing_size}-"

        try:
            with requests.get(
                url,
                headers=headers,
                stream=True,
                allow_redirects=True,
                timeout=self.timeout,
            ) as response:
                if response.status_code not in (200, 206):
                    return DownloadResult(
                        url=url,
                        destination=dest_path,
                        success=False,
                        error_message=f"HTTP status error: {response.status_code}",
                    )

                # Determine total size
                content_length = response.headers.get("Content-Length")
                total_bytes = None
                if content_length is not None:
                    total_bytes = int(content_length) + (
                        existing_size if response.status_code == 206 else 0
                    )

                mode = "ab" if response.status_code == 206 else "wb"
                downloaded = existing_size if response.status_code == 206 else 0

                last_tick = time.time()
                bytes_since_tick = 0
                speed = 0.0

                with open(tmp_path, mode) as f:
                    for chunk in response.iter_content(chunk_size=65536):
                        if not chunk:
                            continue
                        f.write(chunk)
                        downloaded += len(chunk)
                        bytes_since_tick += len(chunk)

                        now = time.time()
                        elapsed = now - last_tick
                        if elapsed >= 0.5:
                            speed = bytes_since_tick / elapsed
                            last_tick = now
                            bytes_since_tick = 0

                        if progress_callback:
                            percent = (
                                (downloaded / total_bytes * 100.0)
                                if total_bytes and total_bytes > 0
                                else 0.0
                            )
                            speed_str = f"{speed / (1024*1024):.1f}MB/s" if speed > 0 else ""
                            progress_callback(
                                DownloadProgress(
                                    url=url,
                                    destination=dest_path,
                                    downloaded_bytes=downloaded,
                                    total_bytes=total_bytes,
                                    speed_text=speed_str,
                                    percent=percent,
                                )
                            )

            # Atomic move on success
            tmp_path.replace(dest_path)
            return DownloadResult(
                url=url,
                destination=dest_path,
                success=True,
                bytes_downloaded=dest_path.stat().st_size,
            )
        except Exception as e:
            return DownloadResult(
                url=url,
                destination=dest_path,
                success=False,
                error_message=str(e),
            )


def download_file(
    url: str,
    destination: Path | str,
    expected_sha256: Optional[str] = None,
    prefer_aria2: bool = True,
    progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
) -> DownloadResult:
    """Convenience helper to download a single file."""
    engine = DownloaderEngine(prefer_aria2=prefer_aria2)
    return engine.download(
        url=url,
        destination=destination,
        expected_sha256=expected_sha256,
        progress_callback=progress_callback,
    )
