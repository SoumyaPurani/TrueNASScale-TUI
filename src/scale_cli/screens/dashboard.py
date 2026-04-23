from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from ..widgets.disk_table import DiskSummaryTable
from ..widgets.pool_table import PoolSummaryTable
from ..widgets.realtime_metrics import RealtimeMetrics
from ..widgets.service_table import ServiceSummaryTable
from ..widgets.system_info import SystemInfoCard

if TYPE_CHECKING:
    from ..app import ScaleApp


class DashboardScreen(Screen):
    BINDINGS = [
        ("q", "app.quit", "Quit"),
        ("d", "app.toggle_dark", "Dark mode"),
        ("r", "app.refresh_data", "Refresh"),
    ]

    def compose(self) -> None:
        app: ScaleApp = self.app  # type: ignore[assignment]
        yield Header()
        yield Static(
            "connecting..." if not app.connected else "connected",
            id="connection-banner",
        )
        with VerticalScroll(id="dashboard-scroll"):
            with Horizontal(id="top-row"):
                yield SystemInfoCard(
                    id="system-info",
                    system_info=app.system_info or {},
                )
                yield RealtimeMetrics(id="realtime-metrics")
            with Horizontal(id="tables-row"):
                yield PoolSummaryTable(id="pool-summary", pools=app.pools or [])
                yield DiskSummaryTable(
                    id="disk-summary",
                    disks=app.disks or [],
                    temps=app.disk_temps or {},
                )
                yield ServiceSummaryTable(
                    id="service-summary", services=app.services or []
                )
        yield Footer()

    def on_mount(self) -> None:
        app: ScaleApp = self.app  # type: ignore[assignment]
        self.watch(app, "connected", self._on_connected_change)
        self.watch(app, "connection_error", self._on_connection_error_change)
        self.watch(app, "system_info", self._on_system_info_change)
        self.watch(app, "realtime", self._on_realtime_change)
        self.watch(app, "pools", self._on_pools_change)
        self.watch(app, "disks", self._on_disks_change)
        self.watch(app, "disk_temps", self._on_disk_temps_change)
        self.watch(app, "services", self._on_services_change)

        self._on_system_info_change(app.system_info or {})
        self._on_realtime_change(app.realtime or {})
        self._on_pools_change(app.pools or [])
        self._on_disks_change(app.disks or [])
        self._on_services_change(app.services or [])

    def _on_connected_change(self, connected: bool) -> None:
        try:
            banner = self.query_one("#connection-banner", Static)
            if connected:
                banner.update("connected")
                banner.styles.color = "green"
            else:
                app: ScaleApp = self.app  # type: ignore[assignment]
                err = app.connection_error
                banner.update(f"disconnected — {err}" if err else "disconnected")
                banner.styles.color = "red"
        except Exception:
            pass

    def _on_connection_error_change(self, error: str) -> None:
        try:
            if error:
                banner = self.query_one("#connection-banner", Static)
                banner.update(f"disconnected — {error}")
                banner.styles.color = "red"
        except Exception:
            pass

    def _on_system_info_change(self, info: dict | None) -> None:
        try:
            card = self.query_one("#system-info", SystemInfoCard)
            card.update_data(info or {})
        except Exception:
            pass

    def _on_realtime_change(self, data: dict | None) -> None:
        try:
            widget = self.query_one("#realtime-metrics", RealtimeMetrics)
            widget.update_data(data or {})
        except Exception:
            pass

    def _on_pools_change(self, pools: list | None) -> None:
        try:
            widget = self.query_one("#pool-summary", PoolSummaryTable)
            widget.update_data(pools or [])
        except Exception:
            pass

    def _on_disks_change(self, disks: list | None) -> None:
        try:
            app: ScaleApp = self.app  # type: ignore[assignment]
            widget = self.query_one("#disk-summary", DiskSummaryTable)
            widget.update_data(disks or [], app.disk_temps or {})
        except Exception:
            pass

    def _on_disk_temps_change(self, temps: dict | None) -> None:
        try:
            app: ScaleApp = self.app  # type: ignore[assignment]
            widget = self.query_one("#disk-summary", DiskSummaryTable)
            widget.update_data(app.disks or [], temps or {})
        except Exception:
            pass

    def _on_services_change(self, services: list | None) -> None:
        try:
            widget = self.query_one("#service-summary", ServiceSummaryTable)
            widget.update_data(services or [])
        except Exception:
            pass

    def _on_connection_error_change(self, error: str) -> None:
        try:
            if error:
                banner = self.query_one("#connection-banner", Static)
                banner.update(f"disconnected — {error}")
                banner.styles.color = "red"
        except Exception as e:
            self.app.log.error(f"Error in handler: {e}")

    def _on_system_info_change(self, info: dict | None) -> None:
        try:
            card = self.query_one("#system-info", SystemInfoCard)
            card.update_data(info or {})
        except Exception as e:
            self.app.log.error(f"Error in handler: {e}")

    def _on_realtime_change(self, data: dict | None) -> None:
        try:
            widget = self.query_one("#realtime-metrics", RealtimeMetrics)
            widget.update_data(data or {})
        except Exception as e:
            self.app.log.error(f"Error in handler: {e}")

    def _on_pools_change(self, pools: list | None) -> None:
        try:
            widget = self.query_one("#pool-summary", PoolSummaryTable)
            widget.update_data(pools or [])
        except Exception as e:
            self.app.log.error(f"Error in handler: {e}")

    def _on_disks_change(self, disks: list | None) -> None:
        try:
            app: ScaleApp = self.app  # type: ignore[assignment]
            widget = self.query_one("#disk-summary", DiskSummaryTable)
            widget.update_data(disks or [], app.disk_temps or {})
        except Exception as e:
            self.app.log.error(f"Error in handler: {e}")

    def _on_disk_temps_change(self, temps: dict | None) -> None:
        try:
            app: ScaleApp = self.app  # type: ignore[assignment]
            widget = self.query_one("#disk-summary", DiskSummaryTable)
            widget.update_data(app.disks or [], temps or {})
        except Exception as e:
            self.app.log.error(f"Error in handler: {e}")

    def _on_services_change(self, services: list | None) -> None:
        try:
            widget = self.query_one("#service-summary", ServiceSummaryTable)
            widget.update_data(services or [])
        except Exception as e:
            self.app.log.error(f"Error in handler: {e}")
