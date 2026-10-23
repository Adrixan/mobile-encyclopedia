"""High-throughput multi-backend resumable downloader with integrity checks."""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tarfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional

import requests

USER_AGENT = "OfflineVault/0.2"
RETRY_STATUSES = {429, 503}
MAX_RETRIES = 3
MAX_RETRY_WAIT_SEC = 60

# Leading bytes identifying each downloadable format
FILE_SIGNATURES: Dict[str, bytes] = {
    "zim": b"ZIM\x04",
    "zip": b"PK\x03\x04",
    "epub": b"PK\x03\x04",
    "map": b"mapsforge binary OSM",
    "apk": b"PK\x03\x04",
    # Z-machine story files start with their version byte
    "z5": b"\x05",
    "z8": b"\x08",
}


def has_aria2() -> bool:
    """Check if aria2c executable is available in PATH."""
    return shutil.which("aria2c") is not None


def sha256_of_file(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_file_hash(path: Path, expected_sha256: str) -> bool:
    """Verify SHA-256 integrity hash of a file."""
    if not path.is_file():
        return False
    return sha256_of_file(path) == expected_sha256.lower()


def check_file_signature(path: Path, fmt: str) -> Optional[str]:
    """Return an error message if the file does not look like the expected format."""
    try:
        with open(path, "rb") as f:
            head = f.read(64)
    except OSError as e:
        return f"Cannot read downloaded file: {e}"
    if not head:
        return "Downloaded file is empty"
    if fmt == "tar":
        if tarfile.is_tarfile(path):
            return None
        return "File signature mismatch: not a tar archive"
    signature = FILE_SIGNATURES.get(fmt)
    if signature is not None and not head.startswith(signature):
        if head.lstrip().lower().startswith((b"<!doctype", b"<html")):
            return f"File signature mismatch: server returned an HTML page instead of a {fmt} file"
        return f"File signature mismatch: not a valid {fmt} file"
    return None


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
        self._sleep: Callable[[float], None] = time.sleep

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
        result = self._download_with_fallback(url, dest_path, tmp_path, progress_callback)

        if result.success and expected_sha256:
            if not verify_file_hash(dest_path, expected_sha256):
                dest_path.unlink(missing_ok=True)
                return DownloadResult(
                    url=url,
                    destination=dest_path,
                    success=False,
                    error_message="SHA-256 checksum verification failed",
                    time_taken_sec=time.time() - start_time,
                )

        result.time_taken_sec = time.time() - start_time
        return result

    def _download_with_fallback(
        self,
        url: str,
        dest_path: Path,
        tmp_path: Path,
        progress_callback: Optional[Callable[[DownloadProgress], None]],
    ) -> DownloadResult:
        """Try aria2c first; on failure restart cleanly with the Python streamer."""
        if self.prefer_aria2 and url.startswith("https://"):
            result = self._download_aria2(url, dest_path, tmp_path, progress_callback)
            if result.success:
                return result
            # aria2c writes segments at scattered offsets; its partial file cannot be
            # resumed by appending, so discard it together with the control file.
            tmp_path.unlink(missing_ok=True)
            tmp_path.with_name(tmp_path.name + ".aria2").unlink(missing_ok=True)
            shutil.rmtree(self._aria2_workdir(tmp_path), ignore_errors=True)
        return self._download_python(url, dest_path, tmp_path, progress_callback)

    @staticmethod
    def _aria2_workdir(tmp_path: Path) -> Path:
        return tmp_path.with_name(tmp_path.name + ".aria2d")

    @staticmethod
    def _aria2_output(workdir: Path, expected_name: str) -> Optional[Path]:
        """Return aria2's finished file; metalinks make aria2 use the upstream file name."""
        expected = workdir / expected_name
        if expected.is_file():
            return expected
        files = [p for p in workdir.iterdir() if p.is_file() and not p.name.endswith(".aria2")] if workdir.is_dir() else []
        return files[0] if len(files) == 1 else None

    def _download_aria2(
        self,
        url: str,
        dest_path: Path,
        tmp_path: Path,
        progress_callback: Optional[Callable[[DownloadProgress], None]],
    ) -> DownloadResult:
        """Download using aria2c with live line streaming for immediate feedback."""
        # Private work dir: Kiwix serves metalinks (mirrors + hashes) and aria2 then
        # saves under the upstream file name, ignoring --out.
        workdir = self._aria2_workdir(tmp_path)
        workdir.mkdir(parents=True, exist_ok=True)
        cmd = [
            "aria2c",
            "--allow-overwrite=true",
            "--auto-file-renaming=false",
            "--follow-metalink=mem",
            "--file-allocation=none",
            f"--user-agent={USER_AGENT}",
            f"--max-connection-per-server={self.split_connections}",
            f"--split={self.split_connections}",
            "--min-split-size=1M",
            "--continue=true",
            "--max-tries=5",
            "--retry-wait=10",
            f"--dir={workdir}",
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

            output = self._aria2_output(workdir, tmp_path.name) if process.returncode == 0 else None
            if output is not None:
                output.replace(dest_path)
                shutil.rmtree(workdir, ignore_errors=True)
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
            reason = f"aria2c exited with code {process.returncode}"
            if process.returncode == 0:
                reason = "aria2c finished but produced no single output file"
            return DownloadResult(
                url=url,
                destination=dest_path,
                success=False,
                error_message=reason,
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
        attempt: int = 0,
    ) -> DownloadResult:
        """Download using Python requests with HTTP Range headers for resuming."""
        existing_size = tmp_path.stat().st_size if tmp_path.exists() else 0
        headers = {"User-Agent": USER_AGENT}
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
                if response.status_code == 416 and existing_size > 0:
                    # Partial no longer matches upstream: restart from scratch
                    tmp_path.unlink(missing_ok=True)
                    return self._download_python(url, dest_path, tmp_path, progress_callback)
                if response.status_code in RETRY_STATUSES and attempt < MAX_RETRIES:
                    # Rate limited or temporarily unavailable: honour Retry-After within a bounded wait
                    retry_after = response.headers.get("Retry-After", "")
                    wait = int(retry_after) if retry_after.isdigit() else 5 * (attempt + 1)
                    response.close()
                    self._sleep(min(wait, MAX_RETRY_WAIT_SEC))
                    return self._download_python(url, dest_path, tmp_path, progress_callback, attempt + 1)
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

            if total_bytes is not None and downloaded != total_bytes:
                return DownloadResult(
                    url=url,
                    destination=dest_path,
                    success=False,
                    error_message=f"Incomplete download: {downloaded} of {total_bytes} bytes",
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
