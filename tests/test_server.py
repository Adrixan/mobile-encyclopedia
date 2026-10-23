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
    init_mimetypes,
)


def test_init_mimetypes():
    init_mimetypes()
    assert mimetypes.types_map.get(".wasm") == "application/wasm" or mimetypes.guess_type("app.wasm")[0] == "application/wasm"
    assert mimetypes.guess_type("data.json")[0] == "application/json"
    assert mimetypes.guess_type("image.svg")[0] == "image/svg+xml"
    assert mimetypes.guess_type("book.epub")[0] == "application/epub+zip"
    assert mimetypes.guess_type("wiki.zim")[0] == "application/x-zim"


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


def _root_app_item():
    return ResourceItem(id="it_tools_suite", name="IT-Tools", category="tools", language="en", format="zip",
                        size_mb=4, upstream_url="https://example.org/it.zip", entrypoint="index.html",
                        serve_root=True, description="Dev utilities")


def test_root_app_ports_only_for_installed_root_apps(tmp_path):
    from offline_vault.server import root_app_ports

    other = ResourceItem(id="cyberchef_suite", name="CyberChef", category="tools", language="en", format="zip",
                         size_mb=1, upstream_url="https://example.org/cc.zip", entrypoint="index.html")
    cat = ResourceCatalog([other, _root_app_item()])
    assert root_app_ports(tmp_path, cat, 8000) == {}
    (tmp_path / "tools" / "it_tools_suite").mkdir(parents=True)
    (tmp_path / "tools" / "it_tools_suite" / "index.html").write_text("<html></html>")
    (tmp_path / "tools" / "cyberchef_suite").mkdir(parents=True)
    assert root_app_ports(tmp_path, cat, 8000) == {"it_tools_suite": 8001}


def test_portal_links_root_app_to_its_port(tmp_path):
    app = tmp_path / "tools" / "it_tools_suite"
    app.mkdir(parents=True)
    (app / "index.html").write_text("<html></html>")
    portal = generate_portal_dashboard(tmp_path, ResourceCatalog([_root_app_item()]), root_ports={"it_tools_suite": 8001})
    content = portal.read_text(encoding="utf-8")
    assert 'data-port="8001"' in content


def test_spa_handler_serves_index_for_client_routes(tmp_path):
    import functools

    from offline_vault.server import SpaRequestHandler

    (tmp_path / "index.html").write_text("<html>spa</html>", encoding="utf-8")
    (tmp_path / "app.js").write_text("js", encoding="utf-8")
    handler = functools.partial(SpaRequestHandler, directory=str(tmp_path))
    server = VaultThreadingServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        conn.request("GET", "/base64-string-converter")
        resp = conn.getresponse()
        assert resp.status == 200 and resp.read() == b"<html>spa</html>"
        conn.request("GET", "/missing.js")
        resp = conn.getresponse()
        resp.read()
        assert resp.status == 404
        conn.close()
    finally:
        server.shutdown()
        server.server_close()


def test_servers_refuse_non_loopback_hosts(tmp_path, capsys):
    from offline_vault.server import is_loopback_host, run_static_server

    assert is_loopback_host("127.0.0.1") and is_loopback_host("localhost") and is_loopback_host("::1")
    assert not is_loopback_host("0.0.0.0") and not is_loopback_host("192.168.1.10")
    assert run_static_server(tmp_path, host="0.0.0.0", port=0) == 1
    assert "localhost only" in capsys.readouterr().out


def test_kiwix_and_kolibri_bind_to_loopback(tmp_path, monkeypatch):
    from offline_vault import server

    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "fresh-data"))
    calls = []
    monkeypatch.setattr(server, "find_kiwix_serve_executable", lambda: "/usr/bin/kiwix-serve")
    monkeypatch.setattr(server, "find_kolibri_executable", lambda: "/usr/bin/kolibri")
    monkeypatch.setattr(server, "ensure_kiwix_library", lambda v: None)
    monkeypatch.setattr(server.subprocess, "run", lambda cmd, **kw: calls.append((cmd, kw.get("env"))))
    (tmp_path / "a.zim").write_bytes(b"ZIM\x04")
    assert server.run_kiwix_server(tmp_path, port=8000) == 0
    assert "--address=127.0.0.1" in calls[-1][0]
    assert server.run_kolibri_server(tmp_path, port=8080) == 0
    assert calls[-1][1]["KOLIBRI_LISTEN_ADDRESS"] == "127.0.0.1"
    # Kolibri refuses to start when the parent of KOLIBRI_HOME is missing (fresh device)
    assert Path(calls[-1][1]["KOLIBRI_HOME"]).is_dir()


def test_cli_serve_defaults_to_localhost_and_rejects_lan(tmp_path):
    with patch("offline_vault.server.run_static_server", return_value=0) as mock_static:
        from offline_vault.cli import run_cli

        assert run_cli(["serve", "--static", "--vault-dir", str(tmp_path)]) == 0
        assert mock_static.call_args.kwargs["host"] == "127.0.0.1"
        assert run_cli(["serve", "--static", "--host", "0.0.0.0", "--vault-dir", str(tmp_path)]) == 2
