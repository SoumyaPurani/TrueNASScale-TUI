from __future__ import annotations

from typing import Any

from textual.widget import Widget
from textual.widgets import DataTable, Static


class PoolSummaryTable(Widget):
    def __init__(
        self, pools: list[dict[str, Any]] | None = None, **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)
        self._pools = pools or []

    def update_data(self, pools: list[dict[str, Any]]) -> None:
        self._pools = pools
        self._render_children()

    def on_mount(self) -> None:
        self._render_children()

    def _render_children(self) -> None:
        for child in list(self.children):
            child.remove()

        self.mount(Static("Pools", classes="card-title"))

        table = DataTable(classes="pool-table")
        table.add_columns("Name", "Status", "Health", "Size")
        for pool in self._pools:
            name = pool.get("name", "—")
            status = pool.get("status", "—")
            health = pool.get("healthy", None)
            health_str = "✓" if health is True else ("✗" if health is False else "—")
            top_level = pool.get("topology", {})
            data_raid = top_level.get("data", [])
            size = ""
            if isinstance(data_raid, list) and data_raid:
                for raid in data_raid:
                    alloc = raid.get("alloc", 0)
                    if isinstance(alloc, (int, float)) and alloc > 0:
                        size = f"{alloc / (1024**3):.1f} GiB"
                        break
            table.add_row(name, status, health_str, size)
        if not self._pools:
            table.add_row("No pools", "", "", "")
        self.mount(table)
