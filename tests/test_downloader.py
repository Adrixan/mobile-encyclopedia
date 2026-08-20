"""Unit and security acceptance tests for US3.1: Resumable Multi-backend Downloader."""

import hashlib
import os
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import pytest

from offline_vault.downloader import (
    DownloaderEngine,
    DownloadProgress,
    DownloadResult,
    has_aria2,
    download_file,
    verify_file_hash,
)
from offline_vault.catalog import ResourceItem


class RangeHTTPRequestHandler(SimpleHTTPRequestHandler):
    """HTTP handler supporting partial content (206) Range requests for resume tests."""

    def do_GET(self):
        path = self.translate_path(self.path)
        if not os.path.exists(path) or os.path.isdir(path):
            self.send_error(404, "File not found")
            return

        file_size = os.path.getsize(path)
        range_header = self.headers.get("Range")

        if range_header:
            # Parse Range: bytes=START-
            try:
                start_str = range_header.strip().replace("bytes=", "").split("-")[0]
                start = int(start_str) if start_str else 0
            except Exception:
                start = 0

            self.send_response(206)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Range", f"bytes {start}-{file_size - 1}/{file_size}")
            self.send_header("Content-Length", str(file_size - start))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()

            with open(path, "rb") as f:
                f.seek(start)
                self.wfile.write(f.read())
        else:
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(file_size))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            with open(path, "rb") as f:
                self.wfile.write(f.read())


@pytest.fixture
def http_server(tmp_path):
    """Spin up local test HTTP server."""
    test_file = tmp_path / "sample.bin"
    sample_data = b"Hello, Offline World! " * 1000  # ~23 KB
    test_file.write_bytes(sample_data)

    class CustomHandler(RangeHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(tmp_path), **kwargs)

    server = HTTPServer(("127.0.0.1", 0), CustomHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield f"http://127.0.0.1:{port}/sample.bin", sample_data

    server.shutdown()


def test_us3_1_detect_aria2():
    # Detects if aria2c exists
    result = has_aria2()
    assert isinstance(result, bool)


def test_us3_1_python_stream_downloader(tmp_path, http_server):
    url, data = http_server
    dest = tmp_path / "out" / "downloaded.bin"

    engine = DownloaderEngine(prefer_aria2=False)
    progress_updates = []

    def on_progress(p: DownloadProgress):
        progress_updates.append(p)

    res: DownloadResult = engine.download(
        url=url,
        destination=dest,
        progress_callback=on_progress,
    )

    assert res.success
    assert dest.exists()
    assert dest.read_bytes() == data
    assert len(progress_updates) > 0
    assert progress_updates[-1].downloaded_bytes == len(data)


def test_us3_1_resumable_download(tmp_path, http_server):
    url, data = http_server
    dest = tmp_path / "resumed.bin"
    tmp_dest = tmp_path / "resumed.bin.tmp"

    # Pre-write partial bytes to .tmp
    partial_bytes = data[:500]
    tmp_dest.write_bytes(partial_bytes)

    engine = DownloaderEngine(prefer_aria2=False)
    res = engine.download(url=url, destination=dest)

    assert res.success
    assert dest.exists()
    assert dest.read_bytes() == data


def test_us3_1_integrity_hash_verification(tmp_path):
    target = tmp_path / "check.bin"
    data = b"Reliable verified content"
    target.write_bytes(data)

    expected_sha256 = hashlib.sha256(data).hexdigest()
    assert verify_file_hash(target, expected_sha256) is True
    assert verify_file_hash(target, "invalid_hash") is False


def test_us3_1_atomic_download_on_failure(tmp_path):
    dest = tmp_path / "should_not_exist.bin"
    engine = DownloaderEngine(prefer_aria2=False)

    # Inexistent port / URL
    res = engine.download("http://127.0.0.1:59999/nonexistent.bin", destination=dest)
    assert res.success is False
    assert not dest.exists()
