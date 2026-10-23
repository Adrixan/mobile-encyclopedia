"""Interactive Textual Terminal UI with live storage budget meter and vault location controls."""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from rich.markup import escape
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
    Markdown,
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
from offline_vault.i18n import set_locale, t
from offline_vault.sync import SyncManager


CATEGORY_BUTTONS = ["all", "admin", "dev", "tutorials", "wiki", "survival", "maps", "qna", "fun", "tools", "apps"]


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
        warning = f"  ⚠️ {escape(t('budget_insufficient'))}" if is_over else ""

        text = (
            f"[bold cyan]{escape(t('budget_available'))}[/bold cyan] {free_gb:.2f} GB  |  "
            f"[bold yellow]{escape(t('budget_selected'))}[/bold yellow] {sel_gb:.2f} GB  |  "
            f"[{status_style}]{escape(t('budget_projected'))}[/{status_style}] {rem_gb:.2f} GB{warning}"
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
            yield Label(f"[bold cyan]{escape(t('path_title'))}[/bold cyan]", classes="title")
            yield Label(f"[dim]{escape(t('path_hint'))}[/dim]")
            with Horizontal(id="preset_bar"):
                yield Button("~/offline_vault", variant="default", id="preset_home")
                yield Button("/sdcard/Download/offline_vault", variant="default", id="preset_sdcard")
            yield Input(value=self.current_path, id="path_input")
            with Horizontal(id="btn_bar"):
                yield Button(t("btn_save"), variant="primary", id="btn_save")
                yield Button(t("btn_cancel"), variant="default", id="btn_cancel")

    @on(Button.Pressed, "#preset_home")
    def on_preset_home(self) -> None:
        self.query_one("#path_input", Input).value = str(Path.home() / "offline_vault")

    @on(Button.Pressed, "#preset_sdcard")
    def on_preset_sdcard(self) -> None:
        self.query_one("#path_input", Input).value = "/sdcard/Download/offline_vault"

    @on(Button.Pressed, "#btn_save")
    def on_save(self) -> None:
        val = self.query_one("#path_input", Input).value.strip()
        self.dismiss(val if val else None)

    @on(Button.Pressed, "#btn_cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)


class HelpScreen(ModalScreen[None]):
    """Modal screen displaying comprehensive usage guide and reader setup instructions."""

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }
    #help_box {
        width: 88;
        height: 85%;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    #help_scroll {
        height: 1fr;
        margin: 1 0;
    }
    """

    HELP_MARKDOWN = """
# 📚 Offline Knowledge Vault Guide

### ⌨️ Keyboard Controls
- **Space**: Toggle selection of highlighted item
- **S**: Download missing or outdated selected items
- **P**: Set / change vault path (presets: `~/offline_vault`, `/sdcard/Download/offline_vault`)
- **A**: Select all visible resources
- **C**: Clear all selections
- **F** / **/**: Focus search & filter bar (`lang:bs`, `cat:wiki`, `tag:security`)
- **H** / **?**: Open this guide, **Esc** closes it
- **R**: Refresh the catalog (latest versions and sizes from upstream)
- **Q**: Quit

---

### 📂 Formats & Folders
Files keep versionless names, so bookmarks survive updates:
- **`.zim`** (all categories): wikis, DevDocs references, Q&A, courses, comics. Open in Kiwix.
- **`.epub`** (`admin/`, `dev/`): books. Open in KOReader.
- **`.map`** (`maps/`): Mapsforge vector maps. Open in Locus Map or OruxMaps.
- **`tools/<id>/`**: prebuilt web apps (CyberChef, IT-Tools, draw.io, Excalidraw, Drawnix, CircuitJS1, SQLime, GeoGebra, periodic table, sun & moon calculators).
- **`.z5` / `.z8`** (`fun/`): interactive fiction. Play with `frotz` in Termux.
- **`apps/*.apk`**: Kiwix, KOReader, Trail Sense, Sky Map, Kolibri for offline installs.
- **`tutorials/kolibri/`**: Kolibri channels (Sikana, CK-12, StoryWeaver). Needs `pip install kolibri`.

**Phone starter set (about 14 GB):** search `tag:starter`, press **A**, then **S**.

---

### 📱 Android
| Content | App | Vault folder |
| :--- | :--- | :--- |
| **`.zim`** | **Kiwix** (Play Store or APK from download.kiwix.org) | any category |
| **`.epub`** | **KOReader** (F-Droid) | `admin/`, `dev/` |
| **`.map`** | **Locus Map** / **OruxMaps** | `maps/` |
| **Web apps** | Browser via `offline-vault serve` in Termux | `tools/` |
| **`.z5` / `.z8`** | `pkg install frotz` in Termux | `fun/` |
| **`.apk`** | File manager: install from file | `apps/` |
| **Kolibri** | **Kolibri** app: import from the vault folder | `tutorials/kolibri/` |

**Kiwix:** the Play Store build opens ZIMs through the file picker; the APK build can scan the vault folder.

**Web apps:** run `offline-vault serve` in Termux and open `http://localhost:8000` in the browser.
IT-Tools, Excalidraw and Drawnix get their own ports (8001, 8002, ...), listed on the portal.

---

### 💻 Local Serving (localhost only)
- `offline-vault serve --static`: portal and web apps at `http://localhost:8000`
- `offline-vault serve --kiwix`: Kiwix server at `http://localhost:8000`
- `offline-vault serve --kolibri`: Kolibri at `http://localhost:8080`
"""

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("q", "close", "Close", show=False),
    ]

    def action_close(self) -> None:
        self.dismiss(None)

    def compose(self) -> ComposeResult:
        with Vertical(id="help_box"):
            with VerticalScroll(id="help_scroll"):
                yield Markdown(self.HELP_MARKDOWN)
            with Horizontal():
                yield Button(t("btn_close_help"), variant="primary", id="btn_close_help")

    @on(Button.Pressed, "#btn_close_help")
    def on_close(self) -> None:
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
            yield Label(f"[bold]{escape(t('sync_title'))}[/bold]", id="sync_title")
            yield Label(t("sync_initializing"), id="sync_status")
            yield ProgressBar(total=len(self.selected_ids), id="overall_progress", show_eta=True)
            yield Label(t("sync_current_file"), id="current_file_label")
            yield ProgressBar(total=100, id="item_progress")
            with Horizontal():
                yield Button(t("btn_done"), variant="success", id="btn_done", disabled=True)
        yield Static("", id="sync_errors")

    def on_mount(self) -> None:
        self.run_sync_worker()

    @work(thread=True)
    def run_sync_worker(self) -> None:
        overall_bar = self.query_one("#overall_progress", ProgressBar)
        item_bar = self.query_one("#item_progress", ProgressBar)
        status_lbl = self.query_one("#sync_status", Label)
        done_btn = self.query_one("#btn_done", Button)

        completed_count = 0
        count_lock = threading.Lock()

        def on_item_progress(item: ResourceItem, p: DownloadProgress) -> None:
            speed_info = f" [cyan]({p.speed_text})[/cyan]" if p.speed_text else ""
            message = escape(t("sync_downloading", category=item.category, name=item.name, percent=f"{p.percent:.1f}"))
            self.app.call_from_thread(status_lbl.update, f"{message}{speed_info}")
            self.app.call_from_thread(item_bar.update, progress=p.percent)

        def on_item_complete(item: ResourceItem, res: DownloadResult) -> None:
            nonlocal completed_count
            with count_lock:
                completed_count += 1
                done = completed_count
            self.app.call_from_thread(overall_bar.update, progress=done)

        summary = self.sync_manager.sync_items(
            set(self.selected_ids),
            force_update=False,
            progress_callback=on_item_progress,
            item_completed_callback=on_item_complete,
        )

        status_style = "bold green" if summary.failed == 0 else "bold yellow"
        status_msg = (
            f"[{status_style}]{escape(t('sync_finished'))}[/{status_style}] "
            + escape(t("sync_summary", completed=summary.completed, skipped=summary.skipped, failed=summary.failed))
        )
        error_lines = "\n".join(
            f"[red]{escape(item_id)}[/red]: {escape(message)}" for item_id, message in summary.errors.items()
        )

        def finish() -> None:
            status_lbl.update(status_msg)
            self.query_one("#sync_errors", Static).update(error_lines)
            done_btn.disabled = False
            done_btn.focus()

        self.app.call_from_thread(finish)

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
    #btn_top_help {
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
        Binding("h", "show_help", "Help"),
        Binding("?", "show_help", "Help"),
        Binding("a", "select_all", "Select All"),
        Binding("c", "clear_all", "Clear"),
        Binding("f", "focus_search", "Search"),
        Binding("slash", "focus_search", "Search", show=False),
        Binding("r", "refresh_catalog", "Refresh"),
    ]

    def __init__(self, config: Optional[VaultConfig] = None) -> None:
        super().__init__()
        self.config = config or load_config()
        set_locale(self.config.locale or "en")
        self.catalog = load_catalog()
        _, _, free_bytes = get_disk_space(self.config.vault_dir)
        self.model = TUIStateModel(self.catalog, free_bytes)
        self.current_rows: List[ResourceItem] = []
        self._sel_column = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="top_vault_bar"):
            yield Label(t("vault_location", path=self.config.vault_dir), id="vault_info_bar", markup=False)
            yield Button(t("btn_set_path"), variant="warning", id="btn_set_path")
            yield Button(t("btn_help"), variant="default", id="btn_top_help")
            yield Button(t("btn_start_sync"), variant="success", id="btn_top_sync")
        yield BudgetBarWidget(id="budget_bar")
        with Horizontal(id="filter_container"):
            yield Input(placeholder=t("search_placeholder"), id="search_input")
            with Horizontal(id="category_bar"):
                for index, category in enumerate(CATEGORY_BUTTONS):
                    yield Button(t(f"cat_{category}"), variant="primary" if index == 0 else "default", id=f"cat_{category}")
        yield DataTable(id="catalog_table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#catalog_table", DataTable)
        table.cursor_type = "row"
        self._sel_column = table.add_columns(
            t("col_sel"), t("col_name"), t("col_category"), t("col_lang"), t("col_format"), t("col_size"),
            t("col_description"),
        )[0]
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

    @on(Button.Pressed, "#btn_top_help")
    def on_btn_top_help_pressed(self) -> None:
        self.action_show_help()

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

    def _refresh_selection_cells(self, items: List[ResourceItem]) -> None:
        """Update only the selection column so the cursor and scroll position stay put."""
        table = self.query_one("#catalog_table", DataTable)
        for item in items:
            mark = "[X]" if item.id in self.model.selected_ids else "[ ]"
            table.update_cell(item.id, self._sel_column, mark)

    def action_toggle_row(self) -> None:
        table = self.query_one("#catalog_table", DataTable)
        if table.cursor_row is not None and 0 <= table.cursor_row < len(self.current_rows):
            item = self.current_rows[table.cursor_row]
            self.model.toggle_item(item.id)
            self._refresh_selection_cells([item])
            self.update_budget_display()

    def action_select_all(self) -> None:
        visible_ids = [item.id for item in self.current_rows]
        self.model.select_all(visible_ids)
        self._refresh_selection_cells(self.current_rows)
        self.update_budget_display()

    def action_clear_all(self) -> None:
        self.model.selected_ids.clear()
        self._refresh_selection_cells(self.current_rows)
        self.update_budget_display()

    def action_focus_search(self) -> None:
        self.query_one("#search_input", Input).focus()

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

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
                    self.query_one("#vault_info_bar", Label).update(t("vault_location", path=self.config.vault_dir))
                    self.update_budget_display()
                    self.notify(t("notify_path_set", path=self.config.vault_dir), severity="information", markup=False)
                except Exception as e:
                    self.notify(t("notify_path_error", error=e), severity="error", markup=False)

        self.push_screen(PathDialog(self.config.vault_dir), on_path_selected)

    def action_refresh_catalog(self) -> None:
        self.notify(t("refresh_started"), severity="information")
        self._refresh_worker()

    @work(thread=True, exclusive=True)
    def _refresh_worker(self) -> None:
        from offline_vault import catalog_builder

        try:
            report = catalog_builder.refresh_user_catalog()
        except Exception as e:  # noqa: BLE001 - surface any refresh problem in the UI
            self.app.call_from_thread(self.notify, t("refresh_failed", error=e), severity="error", markup=False)
            return
        self.app.call_from_thread(self._reload_catalog, report)

    def _reload_catalog(self, report) -> None:
        self.catalog = load_catalog()
        self.model.catalog = self.catalog
        self.model.selected_ids &= {item.id for item in self.catalog.items}
        self.refresh_table()
        self.update_budget_display()
        message = t("refresh_done", items=report.items)
        if report.failed:
            message += ", " + t("refresh_kept", count=len(report.failed))
        self.notify(message, severity="information")

    def action_start_sync(self) -> None:
        if not self.model.selected_ids:
            self.notify(t("notify_no_selection"), severity="warning")
            return
        if self.model.is_over_budget():
            self.notify(t("notify_over_budget"), severity="error")

        self.push_screen(SyncScreen(self.config, self.catalog, self.model.selected_ids))
