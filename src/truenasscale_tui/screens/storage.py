from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual import work
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

if TYPE_CHECKING:
    from ..app import ScaleApp


class StorageScreen(Screen):
    DEFAULT_CSS = """
    StorageScreen {
        layout: vertical;
    }
    StorageScreen #storage-scroll {
        height: 1fr;
    }
    StorageScreen .section-title {
        text-style: bold;
        color: $success;
        margin: 1 0 0 0;
    }
    StorageScreen DataTable {
        height: auto;
    }
    StorageScreen #scrub-info {
        color: $text-muted;
        height: auto;
        padding: 0 1;
    }
    """

    BINDINGS = [
        ("q", "app.quit", "Quit"),
        ("escape", "app.pop_screen", "Back"),
        ("r", "app.refresh_data", "Refresh"),
        ("s", "scrub_selected", "Scrub"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="storage-scroll"):
            yield Static("Pools", classes="section-title")
            yield DataTable(id="pool-table")
            yield Static("", id="scrub-info")
            yield Static("Disks", classes="section-title")
            yield DataTable(id="disk-table")
        yield Footer()

    def on_mount(self) -> None:
        app: ScaleApp = self.app  # type: ignore[assignment]
        pool_table = self.query_one("#pool-table", DataTable)
        pool_table.add_columns("Name", "Status", "Healthy", "Size", "Path")
        pool_table.cursor_type = "row"

        disk_table = self.query_one("#disk-table", DataTable)
        disk_table.add_columns("Identifier", "Model", "Serial", "Size", "Temp")
        disk_table.cursor_type = "row"

        self.watch(app, "pools", self._on_pools_change)
        self.watch(app, "disks", self._on_disks_change)
        self.watch(app, "disk_temps", self._on_temps_change)

        self._populate_pools(app.pools or [])
        self._populate_disks(app.disks or [], app.disk_temps or {})

    def _on_pools_change(self, pools: list[dict[str, Any]] | None) -> None:
        self._populate_pools(pools or [])

    def _on_disks_change(self, disks: list[dict[str, Any]] | None) -> None:
        app: ScaleApp = self.app  # type: ignore[assignment]
        self._populate_disks(disks or [], app.disk_temps or {})

    def _on_temps_change(self, temps: dict[str, Any] | None) -> None:
        app: ScaleApp = self.app  # type: ignore[assignment]
        self._populate_disks(app.disks or [], temps or {})

    def _populate_pools(self, pools: list[dict[str, Any]]) -> None:
        table = self.query_one("#pool-table", DataTable)
        table.clear()
        for pool in pools:
            name = pool.get("name", "—")
            status = pool.get("status", "—")
            healthy = pool.get("healthy", None)
            h_str = "Yes" if healthy is True else "No" if healthy is False else "—"
            top = pool.get("topology", {})
            data_raid = top.get("data", [])
            size = ""
            if isinstance(data_raid, list) and data_raid:
                for raid in data_raid:
                    alloc = raid.get("alloc", 0)
                    if isinstance(alloc, (int, float)) and alloc > 0:
                        size = f"{alloc / (1024**3):.1f} GiB"
                        break
            path = pool.get("path", "—")
            table.add_row(name, status, h_str, size, path)
        if not pools:
            table.add_row("No pools found", "", "", "", "")

    def _populate_disks(
        self, disks: list[dict[str, Any]], temps: dict[str, Any]
    ) -> None:
        table = self.query_one("#disk-table", DataTable)
        table.clear()
        for disk in disks:
            identifier = disk.get("identifier", "—")
            model = disk.get("model", "—")
            serial = disk.get("serial", "—")
            size = disk.get("size", None)
            size_str = (
                f"{size / (1024**3):.1f} GiB"
                if isinstance(size, (int, float)) and size > 0
                else "—"
            )
            dev = disk.get("dev", disk.get("name", ""))
            tv = temps.get(dev, None)
            if isinstance(tv, (int, float)):
                temp_str = f"{tv} C"
            elif isinstance(tv, dict):
                temp_str = f"{tv.get('temperature', '—')} C"
            else:
                temp_str = "—"
            table.add_row(identifier, model, serial, size_str, temp_str)
        if not disks:
            table.add_row("No disks found", "", "", "", "")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = event.data_table
        if table.id == "pool-table":
            row = table.get_row(event.row_key)
            pool_name = row[0]
            self._load_scrub_info(pool_name)

    @work(name="scrub-load", group="scrub", exclusive=True)
    async def _load_scrub_info(self, pool_name: str) -> None:
        app: ScaleApp = self.app  # type: ignore[assignment]
        if not app.connected:
            return
        pools = app.pools
        pool_id = None
        for p in pools:
            if p.get("name") == pool_name:
                pool_id = p.get("id")
                break
        if pool_id is None:
            return
        try:
            state = await app.api.pool_scrub_state(pool_id)
            info = self.query_one("#scrub-info", Static)
            scrub_state = state.get("state", "—")
            pct = state.get("percentage", None)
            eta = state.get("eta", None)
            parts = [f"Scrub: {scrub_state}"]
            if isinstance(pct, (int, float)):
                parts.append(f"{pct:.1f}%")
            if eta:
                parts.append(f"ETA: {eta}")
            info.update("  ".join(parts))
        except Exception:
            info = self.query_one("#scrub-info", Static)
            info.update("Scrub info unavailable")

    def action_scrub_selected(self) -> None:
        table = self.query_one("#pool-table", DataTable)
        if table.row_count > 0:
            try:
                row = table.get_row(table.cursor_row)
                pool_name = row[0]
                self._start_scrub(pool_name)
            except Exception:
                pass

    @work(name="scrub-start", group="scrub", exclusive=True)
    async def _start_scrub(self, pool_name: str) -> None:
        app: ScaleApp = self.app  # type: ignore[assignment]
        if not app.connected:
            return
        pools = app.pools
        pool_id = None
        for p in pools:
            if p.get("name") == pool_name:
                pool_id = p.get("id")
                break
        if pool_id is None:
            return
        try:
            await app.api.pool_scrub(pool_id)
            self.notify(f"Scrub started on {pool_name}")
        except Exception as exc:
            self.notify(f"Scrub failed: {exc}", severity="error")
