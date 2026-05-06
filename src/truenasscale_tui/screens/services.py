from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual import work

from ..api import TrueNASAPIError
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

if TYPE_CHECKING:
    from ..app import ScaleApp


class ServicesScreen(Screen):
    DEFAULT_CSS = """
    ServicesScreen {
        layout: vertical;
    }
    ServicesScreen #services-scroll {
        height: 1fr;
    }
    ServicesScreen .section-title {
        text-style: bold;
        color: $warning;
        margin: 1 0 0 0;
    }
    ServicesScreen DataTable {
        height: auto;
    }
    """

    BINDINGS = [
        ("q", "app.quit", "Quit"),
        ("escape", "app.pop_screen", "Back"),
        ("r", "app.refresh_data", "Refresh"),
        ("enter", "toggle_service", "Toggle"),
        ("s", "start_service", "Start"),
        ("x", "stop_service", "Stop"),
        ("t", "restart_service", "Restart"),
    ]

    def compose(self) -> None:
        yield Header()
        with VerticalScroll(id="services-scroll"):
            yield Static("Services", classes="section-title")
            yield DataTable(id="service-table")
        yield Footer()

    def on_mount(self) -> None:
        app: ScaleApp = self.app  # type: ignore[assignment]
        table = self.query_one("#service-table", DataTable)
        table.add_columns("Service", "State", "Running", "PID")
        table.cursor_type = "row"

        self.watch(app, "services", self._on_services_change)
        self._populate_services(app.services or [])

    def _on_services_change(self, services: list[dict[str, Any]] | None) -> None:
        self._populate_services(services or [])

    def _populate_services(self, services: list[dict[str, Any]]) -> None:
        table = self.query_one("#service-table", DataTable)
        table.clear()
        for svc in services:
            name = svc.get("service", "—")
            state = svc.get("state", "—")
            running = svc.get("running", None)
            r_str = "RUN" if running is True else "STOP" if running is False else "—"
            pid = svc.get("pid", None)
            pid_str = str(pid) if pid is not None else "—"
            table.add_row(name, state, r_str, pid_str)
        if not services:
            table.add_row("No services found", "", "", "")

    def _get_selected_service(self) -> str | None:
        table = self.query_one("#service-table", DataTable)
        if table.row_count == 0:
            return None
        try:
            row = table.get_row(table.cursor_row)
            return row[0]
        except Exception:
            return None

    def action_toggle_service(self) -> None:
        svc = self._get_selected_service()
        if svc is None:
            return
        app: ScaleApp = self.app  # type: ignore[assignment]
        for s in app.services:
            if s.get("service") == svc:
                action = "stop" if s.get("running") else "start"
                self._control_service(svc, action)
                return

    def action_start_service(self) -> None:
        svc = self._get_selected_service()
        if svc:
            self._control_service(svc, "start")

    def action_stop_service(self) -> None:
        svc = self._get_selected_service()
        if svc:
            self._control_service(svc, "stop")

    def action_restart_service(self) -> None:
        svc = self._get_selected_service()
        if svc:
            self._control_service(svc, "restart")

    @work(name="service-control", group="svc-ctrl", exclusive=False)
    async def _control_service(self, service: str, action: str) -> None:
        app: ScaleApp = self.app  # type: ignore[assignment]
        if not app.connected:
            return
        try:
            result = await app.api.service_control(service, action)
            if isinstance(result, bool):
                status = "OK" if result else "failed"
                self.notify(f"{action.capitalize()} {service}: {status}")
            elif isinstance(result, int):
                self.notify(f"{action.capitalize()} {service} (job {result})")
            elif isinstance(result, dict) and "job_id" in result:
                self.notify(f"{action.capitalize()} {service} (job {result['job_id']})")
            else:
                self.notify(f"{action.capitalize()} {service}")
            app.services = await app.api.service_query()
        except TrueNASAPIError as exc:
            hint = ""
            if exc.code == -32602:
                hint = " (invalid params — check service name)"
            elif exc.code in (-32600, 403):
                hint = " (API key may lack write access)"
            self.notify(f"Failed: {exc}{hint}", severity="error")
        except Exception as exc:
            self.notify(f"Failed: {exc}", severity="error")
