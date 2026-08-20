"""Unit and cross-platform integration tests for offline_vault.server."""

import http.client
import mimetypes
import threading
import time
from pathlib import Path
from unittest.mock import patch

from offline_vault.catalog import ResourceCatalog, ResourceItem
from offline_vault.server import (
    VaultThreadingServer,
    find_kiwix_manage_executable,
    find_kiwix_serve_executable,
    find_kolibri_executable,
    generate_portal_dashboard,
    get_lan_ip,
    init_mimetypes,
)


def test_init_mimetypes():
    init_mimetypes()
    assert mimetypes.types_map.get(".wasm") == "application/wasm" or mimetypes.guess_type("app.wasm")[0] == "application/wasm"
    assert mimetypes.guess_type("data.json")[0] == "application/json"
    assert mimetypes.guess_type("image.svg")[0] == "image/svg+xml"
    assert mimetypes.guess_type("book.epub")[0] == "application/epub+zip"
    assert mimetypes.guess_type("wiki.zim")[0] == "application/x-zim"


def test_get_lan_ip():
    ip = get_lan_ip()
    assert isinstance(ip, str)
    assert len(ip.split(".")) == 4 or ip == "127.0.0.1"


def test_generate_portal_dashboard(tmp_path):
    vault_dir = tmp_path / "test_vault"
    vault_dir.mkdir()
    tools_dir = vault_dir / "tools" / "cyberchef_suite"
    tools_dir.mkdir(parents=True)
    (tools_dir / "index.html").write_text("<html>CyberChef</html>", encoding="utf-8")

    item = ResourceItem(
        id="cyberchef_suite",
        name="CyberChef",
        category="tools",
        language="en",
        format="zip",
        size_mb=75,
        upstream_url="https://example.org/cyberchef.zip",
        description="Cyber Swiss Army Knife",
    )
    cat = ResourceCatalog([item])

    portal = generate_portal_dashboard(vault_dir, cat)
    assert portal.exists()
    assert portal.is_file()
    content = portal.read_text(encoding="utf-8")
    assert "Offline Knowledge Vault" in content
    assert "CyberChef" in content
    assert "tools/cyberchef_suite/index.html" in content


def test_vault_threading_server_serves_files(tmp_path):
    import functools
    import http.server

    vault_dir = tmp_path / "vault_srv"
    vault_dir.mkdir()
    (vault_dir / "test.txt").write_text("Hello Offline Vault Server!", encoding="utf-8")
    generate_portal_dashboard(vault_dir)

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(vault_dir))
    # Bind to port 0 (OS picks available ephemeral port)
    server = VaultThreadingServer(("127.0.0.1", 0), handler)
    port = server.server_port

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    time.sleep(0.1)

    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        # Test index.html dashboard
        conn.request("GET", "/")
        resp = conn.getresponse()
        assert resp.status == 200
        body = resp.read().decode("utf-8")
        assert "Offline Knowledge Vault" in body

        # Test static file
        conn.request("GET", "/test.txt")
        resp_file = conn.getresponse()
        assert resp_file.status == 200
        assert resp_file.read().decode("utf-8") == "Hello Offline Vault Server!"
        conn.close()
    finally:
        server.shutdown()
        server.server_close()
