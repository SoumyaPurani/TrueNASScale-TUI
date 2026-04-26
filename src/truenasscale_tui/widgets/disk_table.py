from __future__ import annotations

from typing import Any

from textual.widget import Widget
from textual.widgets import DataTable, Static


class DiskSummaryTable(Widget):
    def __init__(
        self,
        disks: list[dict[str, Any]] | None = None,
        temps: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._disks = disks or []
        self._temps = temps or {}

    def update_data(self, disks: list[dict[str, Any]], temps: dict[str, Any]) -> None:
        self._disks = disks
        self._temps = temps
        self._render_children()

    def on_mount(self) -> None:
        self._render_children()

    def _render_children(self) -> None:
        for child in list(self.children):
            child.remove()

        self.mount(Static("Disks", classes="card-title"))

        table = DataTable(classes="disk-table")
        table.add_columns("Identifier", "Model", "Serial", "Temp")
        for disk in self._disks:
            identifier = disk.get("identifier", "—")
            model = disk.get("model", "—")
            serial = disk.get("serial", "—")
            dev_name = disk.get("dev", disk.get("name", ""))
            temp_val = self._temps.get(dev_name, None)
            if isinstance(temp_val, (int, float)):
                temp_str = f"{temp_val}°C"
            elif isinstance(temp_val, dict):
                temp_str = f"{temp_val.get('temperature', '—')}°C"
            else:
                temp_str = "—"
            table.add_row(identifier, model, serial, temp_str)
        if not self._disks:
            table.add_row("No disks", "", "", "")
        self.mount(table)
