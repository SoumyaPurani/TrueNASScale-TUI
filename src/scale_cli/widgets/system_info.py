from __future__ import annotations

from typing import Any

from textual.widget import Widget
from textual.widgets import Static


class SystemInfoCard(Widget):
    def __init__(
        self,
        system_info: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._system_info = system_info or {}

    def update_data(self, system_info: dict[str, Any]) -> None:
        self._system_info = system_info
        self._render_children()

    def on_mount(self) -> None:
        self._render_children()

    def _render_children(self) -> None:
        for child in list(self.children):
            child.remove()

        d = self._system_info
        rows: list[tuple[str, str]] = []

        rows.append(("Hostname", d.get("hostname") or "—"))
        rows.append(("Version", d.get("version") or "—"))

        uptime_str = d.get("uptime_str")
        if uptime_str:
            rows.append(("Uptime", uptime_str))
        else:
            rows.append(("Uptime", "—"))

        rows.append(("CPU", d.get("model") or "—"))
        rows.append(("Cores", str(d.get("cores") or "—")))

        physmem = d.get("physmem")
        if isinstance(physmem, (int, float)) and physmem > 0:
            rows.append(("Memory", f"{physmem / 1024**3:.1f} GiB"))
        else:
            rows.append(("Memory", "—"))

        self.mount(Static("System", classes="card-title"))
        for label, value in rows:
            self.mount(
                Static(
                    f"[dim]{label:>13s}[/] {value}",
                    classes="info-row",
                )
            )
