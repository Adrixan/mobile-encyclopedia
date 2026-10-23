"""Cross-platform local server runners for Offline Vault (Static Portal, Kiwix, and Kolibri LMS)."""

from __future__ import annotations

import functools
import html
import http.server
import json
import mimetypes
import os
import shutil
import ipaddress
import subprocess
import sys
import threading
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import unquote, urlsplit

from rich.console import Console

from offline_vault.catalog import ResourceCatalog, load_catalog
from offline_vault.config import get_disk_space
from offline_vault.kolibri import (
    find_kolibri_executable,
    kolibri_content_dir,
    kolibri_env,
    kolibri_home_dir,
    kolibri_root,
)


def init_mimetypes() -> None:
    """Ensure all modern web formats, WASM, and archive extensions are mapped."""
    mimetypes.add_type("application/wasm", ".wasm")
    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("application/javascript", ".mjs")
    mimetypes.add_type("application/json", ".json")
    mimetypes.add_type("image/svg+xml", ".svg")
    mimetypes.add_type("application/epub+zip", ".epub")
    mimetypes.add_type("application/x-zim", ".zim")
    mimetypes.add_type("application/octet-stream", ".map")
    mimetypes.add_type("text/markdown", ".md")


DEFAULT_HOST = "127.0.0.1"
LOOPBACK_ONLY_MESSAGE = "Servers listen on localhost only; use 127.0.0.1, ::1 or localhost."


def is_loopback_host(host: str) -> bool:
    """True for loopback addresses (127.0.0.0/8, ::1) and 'localhost'."""
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _bind_address(host: str) -> str:
    """Numeric loopback address for tools that do not resolve names (kiwix-serve, Kolibri)."""
    return "127.0.0.1" if host == "localhost" else host


def find_kiwix_serve_executable() -> Optional[str]:
    """Locate kiwix-serve executable across Linux and Android Termux paths."""
    found = shutil.which("kiwix-serve")
    if found:
        return found

    termux_path = Path("/data/data/com.termux/files/usr/bin/kiwix-serve")
    if termux_path.is_file() and os.access(termux_path, os.X_OK):
        return str(termux_path)

    return None


def find_kiwix_manage_executable() -> Optional[str]:
    """Locate kiwix-manage executable across Linux and Android Termux paths."""
    found = shutil.which("kiwix-manage")
    if found:
        return found

    termux_path = Path("/data/data/com.termux/files/usr/bin/kiwix-manage")
    if termux_path.is_file() and os.access(termux_path, os.X_OK):
        return str(termux_path)

    return None


def rebuild_kiwix_library(vault_dir: Path) -> Optional[Path]:
    """Rebuild library.xml from scratch so replaced ZIMs leave no stale book entries."""
    vault_dir = Path(vault_dir)
    zim_files = sorted(p for p in vault_dir.glob("**/*.zim") if ".tmp" not in p.relative_to(vault_dir).parts)
    library_xml = vault_dir / "library.xml"
    manage_bin = find_kiwix_manage_executable()
    if not zim_files or not manage_bin:
        return library_xml if library_xml.exists() else None

    staging = vault_dir / "library.xml.new"
    staging.unlink(missing_ok=True)
    added = 0
    for z in zim_files:
        try:
            res = subprocess.run([manage_bin, str(staging), "add", str(z)], capture_output=True, check=False)
            added += res.returncode == 0
        except OSError:
            pass
    if added and staging.exists():
        staging.replace(library_xml)
    else:
        staging.unlink(missing_ok=True)
    return library_xml if library_xml.exists() else None


def ensure_kiwix_library(vault_dir: Path) -> Optional[Path]:
    """Auto-discover all ZIM files and (re)build library.xml using kiwix-manage."""
    return rebuild_kiwix_library(vault_dir)


def _load_manifest_entries(vault_dir: Path) -> Dict[str, str]:
    """Map item id to its installed entry URL from the sync manifest."""
    try:
        data = json.loads((vault_dir / ".offline-vault" / "manifest.json").read_text(encoding="utf-8"))
        return {k: v["entry"] for k, v in data.get("items", {}).items() if isinstance(v, dict) and v.get("entry")}
    except (OSError, ValueError, AttributeError):
        return {}


def root_app_ports(vault_dir: Path, catalog: ResourceCatalog, base_port: int) -> Dict[str, int]:
    """Assign base_port+1, +2, ... to installed web apps that only work at a site root."""
    ports: Dict[str, int] = {}
    for item in catalog.items:
        app_dir = Path(vault_dir) / item.category / item.id
        if item.serve_root and (app_dir / "index.html").is_file():
            ports[item.id] = base_port + 1 + len(ports)
    return ports


# Vault internals that must never be served (manifest, partial downloads, logs)
HIDDEN_TOP_LEVEL = {"logs"}


class VaultRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Static handler without directory listings; dotfiles and vault internals answer 404."""

    def _is_hidden(self) -> bool:
        parts = [p for p in unquote(urlsplit(self.path).path).split("/") if p]
        return any(p.startswith(".") for p in parts) or (bool(parts) and parts[0] in HIDDEN_TOP_LEVEL)

    def send_head(self):  # type: ignore[override]
        if self._is_hidden():
            self.send_error(404, "File not found")
            return None
        return super().send_head()

    def list_directory(self, path):  # type: ignore[override]
        self.send_error(404, "File not found")
        return None


class SpaRequestHandler(VaultRequestHandler):
    """Serves index.html for unknown extension-less paths (history-mode single-page apps)."""

    def send_head(self):  # type: ignore[override]
        request_path = urlsplit(self.path).path
        if not os.path.exists(self.translate_path(self.path)) and "." not in request_path.rsplit("/", 1)[-1]:
            self.path = "/index.html"
        return super().send_head()


def generate_portal_dashboard(
    vault_dir: Path,
    catalog: Optional[ResourceCatalog] = None,
    root_ports: Optional[Dict[str, int]] = None,
) -> Path:
    """Generate a lightweight, responsive offline intranet portal at <vault_dir>/index.html."""
    cat = catalog or load_catalog()
    total, used, free = get_disk_space(vault_dir)
    free_gb = free / (1024 * 1024 * 1024)

    # Collect downloaded items
    entries = _load_manifest_entries(vault_dir)
    downloaded_tools: List[Dict[str, str]] = []
    tools_dir = vault_dir / "tools"
    if tools_dir.is_dir():
        for tool_item in cat.filter(category="tools"):
            tool_folder = tools_dir / tool_item.id
            if tool_folder.is_dir():
                entry_rel = entries.get(tool_item.id) or "index.html"
                port = (root_ports or {}).get(tool_item.id)
                downloaded_tools.append({
                    "name": tool_item.name,
                    "desc": tool_item.description,
                    "link": f"http://localhost:{port}/" if port else f"tools/{tool_item.id}/{entry_rel}",
                    "port": str(port) if port else "",
                    "id": tool_item.id,
                })

    downloaded_docs: List[Dict[str, str]] = []
    for cat_name in ["admin", "dev", "tutorials", "survival", "qna", "fun", "apps"]:
        cdir = vault_dir / cat_name
        if cdir.is_dir():
            for item in cat.filter(category=cat_name):
                # Check for extracted folder or canonical file
                folder_entry = cdir / item.id
                file_entry = cdir / f"{item.id}.{item.format}"
                if item.is_archive and folder_entry.is_dir():
                    downloaded_docs.append({
                        "name": item.name,
                        "category": item.category.upper(),
                        "desc": item.description,
                        "link": f"{cat_name}/{item.id}/{entries.get(item.id) or 'index.html'}",
                        "type": "Interactive Web",
                    })
                elif file_entry.exists():
                    downloaded_docs.append({
                        "name": item.name,
                        "category": item.category.upper(),
                        "desc": item.description,
                        "link": f"{cat_name}/{file_entry.name}",
                        "type": item.format.upper(),
                    })

    zim_count = len(list(vault_dir.glob("**/*.zim")))

    # Render HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Offline Knowledge Vault 📚⚡</title>
  <style>
    /* Bioluminescent Night: fonts by name only (no web font downloads, works offline) */
    :root {{
      --bg: #121212;
      --panel: #1E1E1E;
      --panel-glass: rgba(30, 30, 30, 0.72);
      --border: rgba(74, 222, 128, 0.18);
      --text: #E0E0E0;
      --text-muted: #A3A3A3;
      --primary: #4ADE80;
      --secondary: #A7F3D0;
      --alert: #F59E0B;
      --font-heading: "Space Grotesk", "Chakra Petch", system-ui, sans-serif;
      --font-body: "Inter", "Public Sans", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      --font-code: "JetBrains Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: var(--font-body);
      background:
        radial-gradient(60rem 40rem at 85% -10%, rgba(74, 222, 128, 0.10), transparent 60%),
        radial-gradient(40rem 30rem at -10% 110%, rgba(167, 243, 208, 0.06), transparent 60%),
        var(--bg);
      background-attachment: fixed;
      color: var(--text);
      line-height: 1.6;
      padding: 2rem 1rem;
      min-height: 100vh;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    header {{
      padding-bottom: 1.5rem;
      border-bottom: 1px solid var(--border);
      margin-bottom: 2rem;
    }}
    h1, h2, h3 {{ font-family: var(--font-heading); letter-spacing: 0.01em; }}
    h1 {{ font-size: 1.9rem; color: var(--primary); display: flex; align-items: center; gap: 0.5rem; }}
    code {{ font-family: var(--font-code); color: var(--secondary); font-size: 0.9em; }}
    .badge-bar {{ display: flex; gap: 0.75rem; flex-wrap: wrap; margin-top: 0.75rem; }}
    .badge {{
      background: var(--panel-glass);
      border: 1px solid var(--border);
      padding: 0.25rem 0.75rem;
      border-radius: 9999px;
      font-size: 0.85rem;
      color: var(--text-muted);
    }}
    .badge strong {{ color: var(--secondary); }}
    .section-title {{
      font-size: 1.3rem;
      margin: 2rem 0 1rem 0;
      color: var(--secondary);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(min(100%, 300px), 1fr));
      gap: 1.25rem;
      margin-bottom: 2rem;
    }}
    .card {{
      background: var(--panel-glass);
      -webkit-backdrop-filter: blur(12px);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: transform 0.15s, border-color 0.15s;
    }}
    .card:hover {{ transform: translateY(-2px); border-color: var(--primary); }}
    .card h3 {{ font-size: 1.1rem; margin-bottom: 0.5rem; color: var(--text); }}
    .card p {{ font-size: 0.9rem; color: var(--text-muted); margin-bottom: 1rem; flex-grow: 1; }}
    .btn {{
      display: inline-block;
      text-align: center;
      background: var(--primary);
      color: var(--bg);
      font-weight: 600;
      text-decoration: none;
      padding: 0.55rem 1rem;
      border-radius: 0.375rem;
      font-size: 0.9rem;
    }}
    .btn:hover {{ background: var(--secondary); }}
    .btn-outline {{ background: transparent; border: 1px solid var(--primary); color: var(--primary); }}
    .btn-outline:hover {{ background: rgba(74, 222, 128, 0.12); color: var(--secondary); }}
    a:focus-visible, .btn:focus-visible {{ outline: 2px solid var(--secondary); outline-offset: 3px; }}
    .server-box {{
      background: var(--panel-glass);
      -webkit-backdrop-filter: blur(12px);
      backdrop-filter: blur(12px);
      border: 1px dashed var(--border);
      border-left: 3px solid var(--alert);
      border-radius: 0.75rem;
      padding: 1.25rem;
      margin-bottom: 2rem;
    }}
    .server-box h3 {{ color: var(--alert); margin-bottom: 0.5rem; }}
    @media (prefers-reduced-motion: reduce) {{
      .card {{ transition: none; }}
      .card:hover {{ transform: none; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1>Offline Knowledge Vault 📚⚡</h1>
        <div class="badge-bar">
          <span class="badge">Mount Free: <strong>{free_gb:.2f} GB</strong></span>
          <span class="badge">Offline Tools: <strong>{len(downloaded_tools)}</strong></span>
          <span class="badge">Docs & Guides: <strong>{len(downloaded_docs)}</strong></span>
          <span class="badge">ZIM Archives: <strong>{zim_count}</strong></span>
        </div>
      </div>
    </header>

    <div class="server-box">
      <h3>🌐 Local Servers (this device only)</h3>
      <p style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 0.75rem;">
        This vault is served on this device only (localhost):
      </p>
      <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
        <a class="btn btn-outline host-link" data-port="8080" href="http://localhost:8080" target="_blank">🎓 Kolibri LMS (Port 8080)</a>
        <a class="btn btn-outline host-link" data-port="8000" href="http://localhost:8000" target="_blank">📁 Kiwix Server (Port 8000)</a>
      </div>
    </div>

    <h2 class="section-title">🧰 Standalone Offline Web Tools & Applications</h2>
    <div class="grid">
"""

    if downloaded_tools:
        for t in downloaded_tools:
            html_content += f"""      <div class="card">
        <div>
          <h3>{html.escape(t['name'])}</h3>
          <p>{html.escape(t['desc'])}</p>
        </div>
        <a class="btn{' host-link' if t['port'] else ''}" data-port="{t['port']}" href="{html.escape(t['link'], quote=True)}">Launch Tool 🚀</a>
      </div>\n"""
    else:
        html_content += """      <div class="card" style="grid-column: 1 / -1;">
        <p>No tools downloaded yet. Run <code>offline-vault sync --category tools</code> or use the TUI to sync CyberChef, IT-Tools, CircuitJS1, Draw.io, and more!</p>
      </div>\n"""

    html_content += """    </div>

    <h2 class="section-title">📖 Downloaded Documentation & Manuals</h2>
    <div class="grid">
"""

    if downloaded_docs:
        for d in downloaded_docs:
            html_content += f"""      <div class="card">
        <div>
          <span class="badge" style="float: right;">{html.escape(d['category'])}</span>
          <h3>{html.escape(d['name'])}</h3>
          <p>{html.escape(d['desc'])}</p>
        </div>
        <a class="btn btn-outline" href="{html.escape(d['link'], quote=True)}">Open Resource 📂</a>
      </div>\n"""
    else:
        html_content += """      <div class="card" style="grid-column: 1 / -1;">
        <p>No documentation downloaded yet. Run <code>offline-vault sync --category dev</code> or use the TUI to select references and manuals.</p>
      </div>\n"""

    html_content += """    </div>
  </div>
  <script>
    // Point port-based links at the host name this page was opened with (localhost or 127.0.0.1)
    document.querySelectorAll(".host-link").forEach(function (a) {
      a.href = location.protocol + "//" + location.hostname + ":" + a.dataset.port + "/";
    });
  </script>
</body>
</html>"""

    portal_path = vault_dir / "index.html"
    portal_path.write_text(html_content, encoding="utf-8")
    return portal_path


class VaultThreadingServer(http.server.ThreadingHTTPServer):
    """Threading HTTP server with address reuse enabled for instant restarts."""

    allow_reuse_address = True
    daemon_threads = True


def run_static_server(
    vault_dir: Path,
    host: str = DEFAULT_HOST,
    port: int = 8000,
    console: Optional[Console] = None,
) -> int:
    """Run robust multi-threaded static document and tools server."""
    con = console or Console()
    if not is_loopback_host(host):
        con.print(f"[bold red]{LOOPBACK_ONLY_MESSAGE}[/bold red]")
        return 1
    init_mimetypes()
    vault_dir = Path(vault_dir).resolve()
    vault_dir.mkdir(parents=True, exist_ok=True)

    catalog = load_catalog()
    ports = root_app_ports(vault_dir, catalog, port)
    generate_portal_dashboard(vault_dir, catalog, root_ports=ports)

    handler = functools.partial(VaultRequestHandler, directory=str(vault_dir))
    app_servers: List[VaultThreadingServer] = []

    try:
        for item_id, app_port in ports.items():
            item = catalog.get_by_id(item_id)
            app_dir = vault_dir / item.category / item.id
            app_handler = functools.partial(SpaRequestHandler, directory=str(app_dir))
            app_server = VaultThreadingServer((host, app_port), app_handler)
            threading.Thread(target=app_server.serve_forever, daemon=True).start()
            app_servers.append(app_server)

        with VaultThreadingServer((host, port), handler) as httpd:
            con.print(f"[bold green]Offline Static Portal & Web Apps running on port {port}![/bold green]")
            con.print(f" • [cyan]Local PC:[/cyan]      http://localhost:{port}")
            for item_id, app_port in ports.items():
                con.print(f" • [cyan]{catalog.get_by_id(item_id).name}:[/cyan] http://localhost:{app_port} [dim](needs its own site root)[/dim]")
            con.print("[dim]Press Ctrl+C to stop.[/dim]\n")
            httpd.serve_forever()
    except KeyboardInterrupt:
        con.print("\nServer stopped.")
        return 0
    except Exception as e:
        con.print(f"[bold red]Failed to start static server: {e}[/bold red]")
        return 1
    finally:
        for app_server in app_servers:
            app_server.shutdown()
            app_server.server_close()


def run_kolibri_server(
    vault_dir: Path,
    host: str = DEFAULT_HOST,
    port: int = 8080,
    console: Optional[Console] = None,
) -> int:
    """Run Kolibri LMS server using isolated vault storage."""
    con = console or Console()
    if not is_loopback_host(host):
        con.print(f"[bold red]{LOOPBACK_ONLY_MESSAGE}[/bold red]")
        return 1
    vault_dir = Path(vault_dir).resolve()
    kolibri_content_dir(vault_dir).mkdir(parents=True, exist_ok=True)
    kolibri_home_dir().mkdir(parents=True, exist_ok=True)

    kolibri_bin = find_kolibri_executable()
    if not kolibri_bin:
        con.print("[bold red]Kolibri executable not found![/bold red]")
        con.print("\nTo install Kolibri for your platform:")
        con.print(" • [cyan]Linux (Virtualenv/pip):[/cyan] pip install kolibri")
        con.print(" • [cyan]Android (Termux):[/cyan]       pkg install -y python && pip install kolibri")
        con.print(" • [cyan]Android App:[/cyan]            Install Kolibri from F-Droid (org.learningequality.Kolibri)")
        return 1

    con.print(f"[bold cyan]Launching Kolibri LMS on port {port}...[/bold cyan]")
    env = kolibri_env(vault_dir)
    env["KOLIBRI_LISTEN_ADDRESS"] = _bind_address(host)
    con.print(f"[dim]KOLIBRI_CONTENT_DIR: {env['KOLIBRI_CONTENT_DIR']}[/dim]")
    con.print(f"[dim]Other devices: import channels from the folder {kolibri_root(vault_dir)}[/dim]")

    cmd = [kolibri_bin, "start", f"--port={port}", "--foreground"]
    try:
        subprocess.run(cmd, env=env, check=True)
        return 0
    except KeyboardInterrupt:
        con.print("\nKolibri server stopped.")
        return 0
    except Exception as e:
        con.print(f"[bold red]Failed to start Kolibri: {e}[/bold red]")
        return 1


def run_kiwix_server(
    vault_dir: Path,
    host: str = DEFAULT_HOST,
    port: int = 8000,
    console: Optional[Console] = None,
) -> int:
    """Run Kiwix ZIM server using library.xml or discovered ZIM archives."""
    con = console or Console()
    if not is_loopback_host(host):
        con.print(f"[bold red]{LOOPBACK_ONLY_MESSAGE}[/bold red]")
        return 1
    vault_dir = Path(vault_dir).resolve()
    kiwix_bin = find_kiwix_serve_executable()

    if not kiwix_bin:
        con.print("[bold red]kiwix-serve executable not found![/bold red]")
        con.print("\nTo install Kiwix server tools for your platform:")
        con.print(" • [cyan]openSUSE:[/cyan]       sudo zypper in kiwix-tools")
        con.print(" • [cyan]Debian/Ubuntu:[/cyan]  sudo apt install kiwix-tools")
        con.print(" • [cyan]Arch Linux:[/cyan]     sudo pacman -S kiwix-tools")
        con.print(" • [cyan]Android Termux:[/cyan] pkg install -y kiwix-tools")
        con.print(" • [cyan]Android App:[/cyan]    Install Kiwix Mobile from F-Droid (org.kiwix.kiwixmobile)")
        return 1

    library_xml = ensure_kiwix_library(vault_dir)
    zim_files = list(vault_dir.glob("**/*.zim"))

    if not library_xml and not zim_files:
        con.print(f"[bold yellow]No ZIM archives found in {vault_dir}. Falling back to static doc & tools server...[/bold yellow]")
        return run_static_server(vault_dir, host=host, port=port, console=con)

    cmd = [kiwix_bin, f"--address={_bind_address(host)}", f"--port={port}"]
    if library_xml and library_xml.exists():
        cmd.append(f"--library={library_xml}")
    else:
        for z in zim_files:
            cmd.append(str(z))

    con.print(f"[bold green]Starting kiwix-serve on port {port}...[/bold green]")
    try:
        subprocess.run(cmd, check=True)
        return 0
    except KeyboardInterrupt:
        con.print("\nKiwix server stopped.")
        return 0
    except Exception as e:
        con.print(f"[bold red]Failed to start kiwix-serve: {e}[/bold red]")
        return 1
