"""Command-line interface and automation entry point for Offline Vault."""

from __future__ import annotations

import argparse
import http.server
import os
import shutil
import socketserver
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.table import Table

from offline_vault.catalog import ResourceCatalog, load_catalog
from offline_vault.config import VaultConfig, get_disk_space, load_config, save_config, validate_and_resolve_vault_path
from offline_vault.sync import SyncManager
from offline_vault.tui import OfflineVaultApp


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="offline-vault",
        description="Cross-platform offline knowledge manager for Linux and Android Termux.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")

    # TUI
    subparsers.add_parser("tui", help="Launch the interactive Textual TUI")

    # List
    list_p = subparsers.add_parser("list", help="List available resources in catalog")
    list_p.add_argument("--category", "-c", help="Filter by category (admin, dev, wiki, survival, maps, etc.)")
    list_p.add_argument("--language", "-l", help="Filter by language code (en, es, bs, hr, sr, sl, fr, ar)")
    list_p.add_argument("--format", "-f", help="Filter by format (zim, docset, map, epub, html)")
    list_p.add_argument("--query", "-q", help="Search query")

    # Status
    status_p = subparsers.add_parser("status", help="Inspect vault path, disk usage, and downloaded items")
    status_p.add_argument("--vault-dir", help="Override vault directory")

    # Sync
    sync_p = subparsers.add_parser("sync", help="Synchronize / download selected resources non-interactively")
    sync_p.add_argument("--all", action="store_true", help="Sync all catalog resources")
    sync_p.add_argument("--category", "-c", help="Sync all items in category")
    sync_p.add_argument("--language", "-l", help="Filter and sync all items in language")
    sync_p.add_argument("--id", "-i", action="append", help="Specific resource ID(s) to sync")
    sync_p.add_argument("--force", "--update", "-u", action="store_true", help="Force update/re-download and prune old versions")
    sync_p.add_argument("--vault-dir", help="Override vault directory")

    # Serve
    serve_p = subparsers.add_parser("serve", help="Launch local Kolibri LMS, Kiwix, or static HTTP server")
    serve_p.add_argument("--kolibri", action="store_true", help="Start Kolibri offline LMS server")
    serve_p.add_argument("--kiwix", action="store_true", help="Start Kiwix ZIM server")
    serve_p.add_argument("--static", action="store_true", help="Start static HTTP doc & web tools server")
    serve_p.add_argument("--host", default="0.0.0.0", help="Host address to bind on (default: 0.0.0.0)")
    serve_p.add_argument("--port", "-p", type=int, help="Port to listen on (default: 8080 for Kolibri, 8000 for Kiwix/Static)")
    serve_p.add_argument("--vault-dir", help="Override vault directory")

    return parser


def handle_list(args: argparse.Namespace, catalog: ResourceCatalog, console: Console) -> int:
    """Handle 'list' subcommand."""
    items = catalog.items
    if args.category:
        items = catalog.filter(category=args.category)
    if args.language:
        items = [i for i in items if i.language.lower() == args.language.lower()]
    if args.format:
        items = [i for i in items if i.format.lower() == args.format.lower()]
    if args.query:
        items = [i for i in items if i.matches_query(args.query)]

    table = Table(title="Offline Knowledge Catalog", show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Category", style="magenta")
    table.add_column("Lang", style="green")
    table.add_column("Format", style="yellow")
    table.add_column("Size (MB)", justify="right")

    for item in items:
        table.add_row(
            item.id,
            item.name,
            item.category,
            item.language,
            item.format,
            str(item.size_mb),
        )

    console.print(table)
    console.print(f"[dim]Total items listed: {len(items)} | Total catalog size: {sum(i.size_mb for i in items)/1024:.2f} GB[/dim]")
    return 0


def handle_status(args: argparse.Namespace, config: VaultConfig, catalog: ResourceCatalog, console: Console) -> int:
    """Handle 'status' subcommand."""
    vault_dir = Path(args.vault_dir if args.vault_dir else config.vault_dir).resolve()
    total, used, free = get_disk_space(vault_dir)

    console.print(f"[bold cyan]Vault Directory:[/bold cyan] {vault_dir}")
    console.print(f"[bold green]Available Disk Space:[/bold green] {free / (1024**3):.2f} GB / {total / (1024**3):.2f} GB")

    sync_mgr = SyncManager(config, catalog)
    downloaded = []
    missing = []

    for item in catalog.items:
        dest = sync_mgr.get_destination_for_item(item)
        if dest.exists() and dest.stat().st_size > 0:
            downloaded.append((item, dest.stat().st_size))
        else:
            missing.append(item)

    console.print(f"[bold yellow]Downloaded Resources:[/bold yellow] {len(downloaded)} items ({sum(s for _, s in downloaded) / (1024**3):.2f} GB)")
    console.print(f"[dim]Missing / Un-synced Resources: {len(missing)} items[/dim]")
    return 0


def handle_sync(args: argparse.Namespace, config: VaultConfig, catalog: ResourceCatalog, console: Console) -> int:
    """Handle 'sync' subcommand."""
    if args.vault_dir:
        config.vault_dir = str(validate_and_resolve_vault_path(args.vault_dir))

    target_ids = set()
    if args.all:
        target_ids = {i.id for i in catalog.items}
    elif args.id:
        target_ids = set(args.id)
    elif args.category:
        target_ids = {i.id for i in catalog.filter(category=args.category)}
    elif args.language:
        target_ids = {i.id for i in catalog.filter(language=args.language)}
    else:
        console.print("[bold red]Error: Specify --all, --category, --language, or --id to sync.[/bold red]")
        return 1

    console.print(f"[bold cyan]Initiating sync for {len(target_ids)} resources into:[/bold cyan] {config.vault_dir}")
    sync_mgr = SyncManager(config, catalog)

    summary = sync_mgr.sync_items(target_ids, force_update=args.force)
    console.print(
        f"[bold green]Sync Completed:[/bold green] "
        f"Downloaded: {summary.completed}, Skipped: {summary.skipped}, Failed: {summary.failed}"
    )
    if summary.errors:
        for item_id, err in summary.errors.items():
            console.print(f" - [red]{item_id}[/red]: {err}")
    return 0 if summary.failed == 0 else 1


def handle_serve(args: argparse.Namespace, config: VaultConfig, console: Console) -> int:
    """Handle 'serve' subcommand supporting Kolibri LMS, Kiwix, and Static docs."""
    from offline_vault.server import (
        find_kiwix_serve_executable,
        find_kolibri_executable,
        run_kiwix_server,
        run_kolibri_server,
        run_static_server,
    )

    vault_dir = Path(args.vault_dir if args.vault_dir else config.vault_dir).resolve()
    host = getattr(args, "host", "0.0.0.0")

    # 1. Explicit Kolibri flag
    if args.kolibri:
        port = args.port or 8080
        return run_kolibri_server(vault_dir=vault_dir, host=host, port=port, console=console)

    # 2. Explicit Kiwix flag
    if args.kiwix:
        port = args.port or 8000
        return run_kiwix_server(vault_dir=vault_dir, host=host, port=port, console=console)

    # 3. Explicit Static flag
    if args.static:
        port = args.port or 8000
        return run_static_server(vault_dir=vault_dir, host=host, port=port, console=console)

    # 4. Auto-detect: if Kolibri or Kiwix is available and populated, else static server
    if find_kolibri_executable() and (vault_dir / "tutorials" / "kolibri").is_dir():
        port = args.port or 8080
        return run_kolibri_server(vault_dir=vault_dir, host=host, port=port, console=console)
    elif find_kiwix_serve_executable() and list(vault_dir.glob("**/*.zim")):
        port = args.port or 8000
        return run_kiwix_server(vault_dir=vault_dir, host=host, port=port, console=console)
    else:
        port = args.port or 8000
        return run_static_server(vault_dir=vault_dir, host=host, port=port, console=console)


def run_cli(argv: Optional[List[str]] = None) -> int:
    """Main CLI execution router."""
    parser = build_parser()
    args = parser.parse_args(argv)
    console = Console()

    config = load_config()
    catalog = load_catalog()

    if args.command is None or args.command == "tui":
        app = OfflineVaultApp(config=config)
        app.run()
        return 0
    elif args.command == "list":
        return handle_list(args, catalog, console)
    elif args.command == "status":
        return handle_status(args, config, catalog, console)
    elif args.command == "sync":
        return handle_sync(args, config, catalog, console)
    elif args.command == "serve":
        return handle_serve(args, config, console)
    else:
        parser.print_help()
        return 0


def main() -> None:
    """Entry point for offline-vault console script."""
    sys.exit(run_cli(sys.argv[1:]))


if __name__ == "__main__":
    main()
