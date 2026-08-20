"""Interactive Textual Terminal UI with live storage budget meter and vault location controls."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar,
    Static,
)

from offline_vault.catalog import ResourceCatalog, ResourceItem, load_catalog
from offline_vault.config import (
    VaultConfig,
    ensure_vault_structure,
    get_disk_space,
    load_config,
    save_config,
    validate_and_resolve_vault_path,
)
from offline_vault.downloader import DownloadProgress, DownloadResult
from offline_vault.i18n import get_locale, set_locale, t
from offline_vault.sync import SyncManager


class TUIStateModel:
    """State model for selection and storage budget calculation."""

    def __init__(self, catalog: ResourceCatalog, total_free_bytes: int) -> None:
        self.catalog = catalog
        self.total_free_bytes = total_free_bytes
        self.selected_ids: Set[str] = set()
        self.active_category: Optional[str] = None
        self.active_language: Optional[str] = None
        self.search_query: str = ""

    @property
    def total_free_mb(self) -> int:
        return self.total_free_bytes // (1024 * 1024)

    def toggle_item(self, item_id: str) -> bool:
        """Toggle selection state of item. Return new is_selected."""
        if item_id in self.selected_ids:
            self.selected_ids.remove(item_id)
            return False
        else:
            self.selected_ids.add(item_id)
            return True

    def select_all(self, item_ids: List[str]) -> None:
        self.selected_ids.update(item_ids)

    def deselect_all(self, item_ids: List[str]) -> None:
        for i in item_ids:
            self.selected_ids.discard(i)

    def get_selected_size_mb(self) -> int:
        return self.catalog.calculate_total_size_mb(self.selected_ids)

    def get_projected_remaining_mb(self) -> int:
        return self.total_free_mb - self.get_selected_size_mb()

    def is_over_budget(self) -> bool:
        return self.get_projected_remaining_mb() < 0

    def filter_items(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        language: Optional[str] = None,
    ) -> List[ResourceItem]:
        items = self.catalog.items
        if category and category != "all":
            items = [i for i in items if i.category.lower() == category.lower()]
        if language and language != "all":
            items = [i for i in items if i.language.lower() == language.lower()]
        if query:
            items = [i for i in items if i.matches_query(query)]
        return items


class BudgetBarWidget(Static):
    """Storage budget meter displaying real-time space calculation."""

    def update_budget(self, free_mb: int, selected_mb: int, remaining_mb: int, is_over: bool) -> None:
        free_gb = free_mb / 1024.0
        sel_gb = selected_mb / 1024.0
        rem_gb = remaining_mb / 1024.0

        status_style = "bold red" if is_over else "bold green"
        warning = " [⚠️ INSUFFICIENT DISK SPACE]" if is_over else ""

        text = (
            f"[bold cyan]Available Mount Space:[/bold cyan] {free_gb:.2f} GB  |  "
            f"[bold yellow]Selected:[/bold yellow] {sel_gb:.2f} GB  |  "
            f"[{status_style}]Projected Free:[/{status_style}] {rem_gb:.2f} GB{warning}"
        )
        self.update(text)


class PathDialog(ModalScreen[Optional[str]]):
    """Modal dialog to configure vault directory path with presets."""

    DEFAULT_CSS = """
    PathDialog {
        align: center middle;
    }
    #dialog_box {
        width: 70;
        height: auto;
        border: solid $accent;
        background: $surface;
        padding: 1 2;
    }
    #preset_bar {
        margin: 1 0;
        height: 3;
    }
    #preset_bar Button {
        margin-right: 1;
    }
    #path_input {
        margin: 1 0;
    }
    #btn_bar {
        align: right middle;
    }
    """

    def __init__(self, current_path: str) -> None:
        super().__init__()
        self.current_path = current_path

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog_box"):
            yield Label("[bold cyan]Set Offline Vault Storage Directory[/bold cyan]", classes="title")
            yield Label("[dim]Select a preset or type a custom destination folder path:[/dim]")
            with Horizontal(id="preset_bar"):
                yield Button("~/offline_vault", variant="default", id="preset_home")
                yield Button("/sdcard/Download/offline_vault", variant="default", id="preset_sdcard")
                yield Button("/tmp/offline_vault", variant="default", id="preset_tmp")
            yield Input(value=self.current_path, id="path_input")
            with Horizontal(id="btn_bar"):
                yield Button("Save & Apply", variant="primary", id="btn_save")
                yield Button("Cancel", variant="default", id="btn_cancel")

    @on(Button.Pressed, "#preset_home")
    def on_preset_home(self) -> None:
        self.query_one("#path_input", Input).value = str(Path.home() / "offline_vault")

    @on(Button.Pressed, "#preset_sdcard")
    def on_preset_sdcard(self) -> None:
        self.query_one("#path_input", Input).value = "/sdcard/Download/offline_vault"

    @on(Button.Pressed, "#preset_tmp")
    def on_preset_tmp(self) -> None:
        self.query_one("#path_input", Input).value = "/tmp/offline_vault"

    @on(Button.Pressed, "#btn_save")
    def on_save(self) -> None:
        val = self.query_one("#path_input", Input).value.strip()
        self.dismiss(val if val else None)

    @on(Button.Pressed, "#btn_cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)


class SyncScreen(ModalScreen[None]):
    """Modal screen displaying live download and indexing progress."""

    DEFAULT_CSS = """
    SyncScreen {
        align: center middle;
    }
    #sync_box {
        width: 80;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    #item_progress {
        margin: 1 0;
    }
    """

    def __init__(self, config: VaultConfig, catalog: ResourceCatalog, selected_ids: Set[str]) -> None:
        super().__init__()
        self.config = config
        self.catalog = catalog
        self.selected_ids = selected_ids
        self.sync_manager = SyncManager(config, catalog)

    def compose(self) -> ComposeResult:
        with Vertical(id="sync_box"):
            yield Label("[bold]Synchronizing Offline Knowledge Vault[/bold]", id="sync_title")
            yield Label("Initializing transfers...", id="sync_status")
            yield ProgressBar(total=len(self.selected_ids), id="overall_progress", show_eta=True)
            yield Label("Current File Progress:", id="current_file_label")
            yield ProgressBar(total=100, id="item_progress")
            with Horizontal():
                yield Button("Close / Done", variant="success", id="btn_done", disabled=True)

    def on_mount(self) -> None:
        self.run_sync_worker()

    @work(thread=True)
    def run_sync_worker(self) -> None:
        overall_bar = self.query_one("#overall_progress", ProgressBar)
        item_bar = self.query_one("#item_progress", ProgressBar)
        status_lbl = self.query_one("#sync_status", Label)
        done_btn = self.query_one("#btn_done", Button)

        completed_count = 0

        def on_item_progress(item: ResourceItem, p: DownloadProgress) -> None:
            speed_info = f" [cyan]({p.speed_text})[/cyan]" if p.speed_text else ""
            self.app.call_from_thread(
                status_lbl.update,
                f"Downloading to [magenta]{item.category}/[/magenta]: [bold]{item.name}[/bold] ({p.percent:.1f}%){speed_info}"
            )
            self.app.call_from_thread(item_bar.update, progress=p.percent)

        def on_item_complete(item: ResourceItem, res: DownloadResult) -> None:
            nonlocal completed_count
            completed_count += 1
            self.app.call_from_thread(overall_bar.update, progress=completed_count)

        summary = self.sync_manager.sync_items(
            self.selected_ids,
            force_update=True,
            progress_callback=on_item_progress,
            item_completed_callback=on_item_complete,
        )

        status_msg = (
            f"[bold green]Sync Finished![/bold green] "
            f"Completed: {summary.completed}, Skipped (Already Present): {summary.skipped}, Failed: {summary.failed}"
        )
        self.app.call_from_thread(status_lbl.update, status_msg)
        self.app.call_from_thread(done_btn.set_class, False, "disabled")
        done_btn.disabled = False

    @on(Button.Pressed, "#btn_done")
    def on_done(self) -> None:
        self.dismiss(None)


class OfflineVaultApp(App):
    """Main Textual Application for Offline Vault."""

    CSS = """
    Screen {
        layout: vertical;
        background: $background;
        color: $text;
    }
    #top_vault_bar {
        background: $surface;
        padding: 0 1;
        height: 3;
        align: left middle;
    }
    #vault_info_bar {
        width: 1fr;
        color: $text-muted;
    }
    #btn_set_path {
        margin-right: 1;
    }
    #budget_bar {
        background: $panel;
        border: round $accent;
        padding: 0 1;
        height: 3;
        margin: 0 1;
    }
    #filter_container {
        height: 3;
        margin: 0 1;
        align: left middle;
    }
    #search_input {
        width: 40;
    }
    #category_bar {
        margin-left: 1;
    }
    DataTable {
        height: 1fr;
        margin: 0 1 1 1;
        border: solid $primary;
    }
    DataTable > .datatable--cursor {
        background: $primary 30%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("space", "toggle_row", "Toggle Item"),
        Binding("s", "start_sync", "Start Sync"),
        Binding("p", "change_path", "Set Path"),
        Binding("a", "select_all", "Select All"),
        Binding("c", "clear_all", "Clear"),
        Binding("f", "focus_search", "Search"),
    ]

    def __init__(self, config: Optional[VaultConfig] = None) -> None:
        super().__init__()
        self.config = config or load_config()
        self.catalog = load_catalog()
        _, _, free_bytes = get_disk_space(self.config.vault_dir)
        self.model = TUIStateModel(self.catalog, free_bytes)
        self.current_rows: List[ResourceItem] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="top_vault_bar"):
            yield Label(f"📁 Vault Location: {self.config.vault_dir}", id="vault_info_bar")
            yield Button("📂 Set Vault Location (P)", variant="warning", id="btn_set_path")
            yield Button("⚡ Start Sync (S)", variant="success", id="btn_top_sync")
        yield BudgetBarWidget(id="budget_bar")
        with Horizontal(id="filter_container"):
            yield Input(placeholder="Filter (e.g. opensuse, lang:bs, admin)...", id="search_input")
            with Horizontal(id="category_bar"):
                yield Button("All", variant="primary", id="cat_all")
                yield Button("Admin", variant="default", id="cat_admin")
                yield Button("Dev", variant="default", id="cat_dev")
                yield Button("Tutorials", variant="default", id="cat_tutorials")
                yield Button("Wikis", variant="default", id="cat_wiki")
                yield Button("Survival", variant="default", id="cat_survival")
                yield Button("Maps", variant="default", id="cat_maps")
                yield Button("Q&A", variant="default", id="cat_qna")
                yield Button("Comics", variant="default", id="cat_fun")
        yield DataTable(id="catalog_table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#catalog_table", DataTable)
        table.cursor_type = "row"
        table.add_columns("Sel", "Name", "Category", "Lang", "Format", "Size (MB)", "Description")
        self.refresh_table()
        self.update_budget_display()

    def update_budget_display(self) -> None:
        budget_widget = self.query_one("#budget_bar", BudgetBarWidget)
        budget_widget.update_budget(
            free_mb=self.model.total_free_mb,
            selected_mb=self.model.get_selected_size_mb(),
            remaining_mb=self.model.get_projected_remaining_mb(),
            is_over=self.model.is_over_budget(),
        )

    def refresh_table(self) -> None:
        table = self.query_one("#catalog_table", DataTable)
        table.clear()
        self.current_rows = self.model.filter_items(
            query=self.model.search_query,
            category=self.model.active_category,
            language=self.model.active_language,
        )

        for item in self.current_rows:
            is_sel = "[X]" if item.id in self.model.selected_ids else "[ ]"
            table.add_row(
                is_sel,
                item.name,
                item.category.upper(),
                item.language.upper(),
                item.format.upper(),
                str(item.size_mb),
                item.description,
                key=item.id,
            )

    @on(Input.Changed, "#search_input")
    def on_search_changed(self, event: Input.Changed) -> None:
        self.model.search_query = event.value
        self.refresh_table()

    @on(Button.Pressed, "#btn_set_path")
    def on_btn_set_path_pressed(self) -> None:
        self.action_change_path()

    @on(Button.Pressed, "#btn_top_sync")
    def on_btn_top_sync_pressed(self) -> None:
        self.action_start_sync()

    @on(Button.Pressed, "#category_bar Button")
    def on_category_pressed(self, event: Button.Pressed) -> None:
        if not event.button.id:
            return
        cat_id = event.button.id.replace("cat_", "")
        self.model.active_category = None if cat_id == "all" else cat_id
        # Update button variants
        for btn in self.query("#category_bar Button"):
            btn.variant = "primary" if btn.id == event.button.id else "default"
        self.refresh_table()

    def action_toggle_row(self) -> None:
        table = self.query_one("#catalog_table", DataTable)
        if table.cursor_row is not None and 0 <= table.cursor_row < len(self.current_rows):
            item = self.current_rows[table.cursor_row]
            self.model.toggle_item(item.id)
            self.refresh_table()
            self.update_budget_display()

    def action_select_all(self) -> None:
        visible_ids = [item.id for item in self.current_rows]
        self.model.select_all(visible_ids)
        self.refresh_table()
        self.update_budget_display()

    def action_clear_all(self) -> None:
        self.model.selected_ids.clear()
        self.refresh_table()
        self.update_budget_display()

    def action_focus_search(self) -> None:
        self.query_one("#search_input", Input).focus()

    def action_change_path(self) -> None:
        def on_path_selected(new_path: Optional[str]) -> None:
            if new_path:
                try:
                    resolved = validate_and_resolve_vault_path(new_path, create_if_missing=True)
                    ensure_vault_structure(resolved)
                    self.config.vault_dir = str(resolved)
                    save_config(self.config)
                    _, _, free = get_disk_space(resolved)
                    self.model.total_free_bytes = free
                    self.query_one("#vault_info_bar", Label).update(f"📁 Vault Location: {self.config.vault_dir}")
                    self.update_budget_display()
                    self.notify(f"Vault location set to: {self.config.vault_dir}", severity="information")
                except Exception as e:
                    self.notify(f"Error setting path: {e}", severity="error")

        self.push_screen(PathDialog(self.config.vault_dir), on_path_selected)

    def action_start_sync(self) -> None:
        if not self.model.selected_ids:
            self.notify("No resources selected to sync!", severity="warning")
            return
        if self.model.is_over_budget():
            self.notify("Warning: Selected resources exceed available disk space!", severity="error")

        self.push_screen(SyncScreen(self.config, self.catalog, self.model.selected_ids))
