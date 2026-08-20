"""Cross-platform local server runners for Offline Vault (Static Portal, Kiwix, and Kolibri LMS)."""

from __future__ import annotations

import functools
import http.server
import mimetypes
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console

from offline_vault.catalog import ResourceCatalog, load_catalog
from offline_vault.config import VaultConfig, get_disk_space, load_config


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


def get_lan_ip() -> str:
    """Discover primary outbound LAN IP address for network display without connecting outside."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def find_kolibri_executable() -> Optional[str]:
    """Locate Kolibri executable in active virtualenv, sys.path, or system PATH."""
    venv_kolibri = Path(sys.executable).parent / "kolibri"
    if venv_kolibri.is_file() and os.access(venv_kolibri, os.X_OK):
        return str(venv_kolibri)

    global_kolibri = shutil.which("kolibri")
    if global_kolibri:
        return global_kolibri

    return None


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


def ensure_kiwix_library(vault_dir: Path) -> Optional[Path]:
    """Auto-discover all ZIM files and update library.xml using kiwix-manage."""
    zim_files = list(vault_dir.glob("**/*.zim"))
    if not zim_files:
        return None

    library_xml = vault_dir / "library.xml"
    manage_bin = find_kiwix_manage_executable()

    if manage_bin:
        for z in zim_files:
            try:
                subprocess.run([manage_bin, str(library_xml), "add", str(z)], capture_output=True, check=False)
            except Exception:
                pass

    return library_xml if library_xml.exists() else None


def generate_portal_dashboard(vault_dir: Path, catalog: Optional[ResourceCatalog] = None) -> Path:
    """Generate a lightweight, responsive offline intranet portal at <vault_dir>/index.html."""
    cat = catalog or load_catalog()
    total, used, free = get_disk_space(vault_dir)
    free_gb = free / (1024 * 1024 * 1024)

    # Collect downloaded items
    downloaded_tools: List[Dict[str, str]] = []
    tools_dir = vault_dir / "tools"
    if tools_dir.is_dir():
        for tool_item in cat.filter(category="tools"):
            tool_folder = tools_dir / tool_item.id
            index_path = tool_folder / "index.html"
            if index_path.exists() or tool_folder.is_dir():
                # Find entrypoint
                entry = f"tools/{tool_item.id}/index.html" if index_path.exists() else f"tools/{tool_item.id}/"
                downloaded_tools.append({
                    "name": tool_item.name,
                    "desc": tool_item.description,
                    "link": entry,
                    "id": tool_item.id,
                })

    downloaded_docs: List[Dict[str, str]] = []
    for cat_name in ["admin", "dev", "tutorials", "survival", "qna", "fun"]:
        cdir = vault_dir / cat_name
        if cdir.is_dir():
            for item in cat.filter(category=cat_name):
                # Check for extracted folder or canonical file
                folder_entry = cdir / item.id / "index.html"
                file_entry = cdir / f"{item.id}.{item.format}"
                if folder_entry.exists():
                    downloaded_docs.append({
                        "name": item.name,
                        "category": item.category.upper(),
                        "desc": item.description,
                        "link": f"{cat_name}/{item.id}/index.html",
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
    :root {{
      --bg: #0f172a;
      --card-bg: #1e293b;
      --card-border: #334155;
      --primary: #38bdf8;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --accent: #22c55e;
      --accent-orange: #f59e0b;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
      padding: 1.5rem;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    header {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 1.5rem;
      border-bottom: 1px solid var(--card-border);
      margin-bottom: 2rem;
    }}
    h1 {{ font-size: 1.8rem; color: var(--primary); display: flex; align-items: center; gap: 0.5rem; }}
    .badge-bar {{ display: flex; gap: 0.75rem; flex-wrap: wrap; margin-top: 0.5rem; }}
    .badge {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      padding: 0.25rem 0.75rem;
      border-radius: 9999px;
      font-size: 0.85rem;
      color: var(--text-muted);
    }}
    .badge strong {{ color: var(--text); }}
    .section-title {{
      font-size: 1.3rem;
      margin: 1.5rem 0 1rem 0;
      color: var(--primary);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 1.25rem;
      margin-bottom: 2rem;
    }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 0.75rem;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: transform 0.15s, border-color 0.15s;
    }}
    .card:hover {{
      transform: translateY(-2px);
      border-color: var(--primary);
    }}
    .card h3 {{ font-size: 1.1rem; margin-bottom: 0.5rem; color: var(--text); }}
    .card p {{ font-size: 0.9rem; color: var(--text-muted); margin-bottom: 1rem; flex-grow: 1; }}
    .btn {{
      display: inline-block;
      text-align: center;
      background: var(--primary);
      color: #0f172a;
      font-weight: 600;
      text-decoration: none;
      padding: 0.5rem 1rem;
      border-radius: 0.375rem;
      font-size: 0.9rem;
    }}
    .btn:hover {{ background: #7dd3fc; }}
    .btn-outline {{
      background: transparent;
      border: 1px solid var(--primary);
      color: var(--primary);
    }}
    .btn-outline:hover {{ background: rgba(56, 189, 248, 0.1); }}
    .server-box {{
      background: rgba(56, 189, 248, 0.05);
      border: 1px dashed var(--primary);
      border-radius: 0.75rem;
      padding: 1.25rem;
      margin-bottom: 2rem;
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
      <h3 style="color: var(--primary); margin-bottom: 0.5rem;">🌐 Local Servers & Intranet Access</h3>
      <p style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 0.75rem;">
        This vault is served locally on your machine and across your Wi-Fi hotspot:
      </p>
      <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
        <a class="btn btn-outline" href="http://localhost:8080" target="_blank">🎓 Kolibri LMS (Port 8080)</a>
        <a class="btn btn-outline" href="http://localhost:8000" target="_blank">📁 Kiwix Server (Port 8000)</a>
      </div>
    </div>

    <h2 class="section-title">🧰 Standalone Offline Web Tools & Applications</h2>
    <div class="grid">
"""

    if downloaded_tools:
        for t in downloaded_tools:
            html_content += f"""      <div class="card">
        <div>
          <h3>{t['name']}</h3>
          <p>{t['desc']}</p>
        </div>
        <a class="btn" href="{t['link']}">Launch Tool 🚀</a>
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
          <span class="badge" style="float: right;">{d['category']}</span>
          <h3>{d['name']}</h3>
          <p>{d['desc']}</p>
        </div>
        <a class="btn btn-outline" href="{d['link']}">Open Resource 📂</a>
      </div>\n"""
    else:
        html_content += """      <div class="card" style="grid-column: 1 / -1;">
        <p>No documentation downloaded yet. Run <code>offline-vault sync --category dev</code> or use the TUI to select docsets and manuals.</p>
      </div>\n"""

    html_content += """    </div>
  </div>
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
    host: str = "0.0.0.0",
    port: int = 8000,
    console: Optional[Console] = None,
) -> int:
    """Run robust multi-threaded static document and tools server."""
    con = console or Console()
    init_mimetypes()
    vault_dir = Path(vault_dir).resolve()
    vault_dir.mkdir(parents=True, exist_ok=True)

    # Generate dashboard
    generate_portal_dashboard(vault_dir)

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(vault_dir))
    lan_ip = get_lan_ip()

    try:
        with VaultThreadingServer((host, port), handler) as httpd:
            con.print(f"[bold green]Offline Static Portal & Web Apps running on port {port}![/bold green]")
            con.print(f" • [cyan]Local PC:[/cyan]      http://localhost:{port}")
            if lan_ip != "127.0.0.1":
                con.print(f" • [cyan]Local Network:[/cyan] http://{lan_ip}:{port} [dim](open on phone/tablet over Wi-Fi/Hotspot)[/dim]")
            con.print("[dim]Press Ctrl+C to stop.[/dim]\n")
            httpd.serve_forever()
    except KeyboardInterrupt:
        con.print("\nServer stopped.")
        return 0
    except Exception as e:
        con.print(f"[bold red]Failed to start static server: {e}[/bold red]")
        return 1


def run_kolibri_server(
    vault_dir: Path,
    host: str = "0.0.0.0",
    port: int = 8080,
    console: Optional[Console] = None,
) -> int:
    """Run Kolibri LMS server using isolated vault storage."""
    con = console or Console()
    vault_dir = Path(vault_dir).resolve()
    kolibri_dir = vault_dir / "tutorials" / "kolibri"
    kolibri_dir.mkdir(parents=True, exist_ok=True)

    kolibri_bin = find_kolibri_executable()
    if not kolibri_bin:
        con.print("[bold red]Kolibri executable not found![/bold red]")
        con.print("\nTo install Kolibri for your platform:")
        con.print(" • [cyan]Linux (Virtualenv/pip):[/cyan] pip install kolibri")
        con.print(" • [cyan]Android (Termux):[/cyan]       pkg install -y python && pip install kolibri")
        con.print(" • [cyan]Android App:[/cyan]            Install Kolibri from F-Droid (org.learningequality.Kolibri)")
        return 1

    con.print(f"[bold cyan]Launching Kolibri LMS on port {port}...[/bold cyan]")
    con.print(f"[dim]KOLIBRI_HOME: {kolibri_dir}[/dim]")
    env = os.environ.copy()
    env["KOLIBRI_HOME"] = str(kolibri_dir)

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
    host: str = "0.0.0.0",
    port: int = 8000,
    console: Optional[Console] = None,
) -> int:
    """Run Kiwix ZIM server using library.xml or discovered ZIM archives."""
    con = console or Console()
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

    cmd = [kiwix_bin, f"--port={port}"]
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
