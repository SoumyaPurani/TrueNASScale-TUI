from __future__ import annotations

from typing import Any

from textual.widget import Widget
from textual.widgets import DataTable, Static


class ServiceSummaryTable(Widget):
    def __init__(
        self, services: list[dict[str, Any]] | None = None, **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)
        self._services = services or []

    def update_data(self, services: list[dict[str, Any]]) -> None:
        self._services = services
        self._render_children()

    def on_mount(self) -> None:
        self._render_children()

    def _render_children(self) -> None:
        for child in list(self.children):
            child.remove()

        self.mount(Static("Services", classes="card-title"))

        table = DataTable(classes="service-table")
        table.add_columns("Service", "State", "Running")
        for svc in self._services:
            name = svc.get("service", "—")
            state = svc.get("state", "—")
            running = svc.get("running", None)
            run_str = "●" if running is True else "○" if running is False else "—"
            table.add_row(name, state, run_str)
        if not self._services:
            table.add_row("No services", "", "")
        self.mount(table)
