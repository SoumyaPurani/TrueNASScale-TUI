from __future__ import annotations

import asyncio
import logging
from typing import Any

from textual import work
from textual.app import App
from textual.reactive import reactive

from .api import TrueNASAPIError, TrueNASWSClient
from .config import ScaleConfig, load_config
from .screens.dashboard import DashboardScreen
from .screens.first_run import FirstRunScreen
from .screens.services import ServicesScreen
from .screens.settings import SettingsScreen
from .screens.storage import StorageScreen

logger = logging.getLogger(__name__)


class ScaleApp(App[None]):
    CSS_PATH = "tui.css"
    TITLE = "scale-cli"
    SUB_TITLE = "TrueNAS Scale TUI"

    SCREENS = {
        "dashboard": DashboardScreen,
        "storage": StorageScreen,
        "services": ServicesScreen,
        "first_run": FirstRunScreen,
        "settings": SettingsScreen,
    }

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Dark mode"),
        ("r", "refresh_data", "Refresh"),
        ("1", "switch_screen('dashboard')", "Dashboard"),
        ("2", "switch_screen('storage')", "Storage"),
        ("3", "switch_screen('services')", "Services"),
        ("c", "settings", "Settings"),
        ("l", "logout", "Logout"),
    ]

    connected: reactive[bool] = reactive(False)
    connection_error: reactive[str] = reactive("")
    system_info: reactive[dict[str, Any]] = reactive(dict)
    realtime: reactive[dict[str, Any]] = reactive(dict)
    pools: reactive[list[dict[str, Any]]] = reactive(list)
    disks: reactive[list[dict[str, Any]]] = reactive(list)
    disk_temps: reactive[dict[str, Any]] = reactive(dict)
    services: reactive[list[dict[str, Any]]] = reactive(list)

    def __init__(self, config: ScaleConfig | None = None) -> None:
        super().__init__()
        self._config = config or load_config()
        self._api: TrueNASWSClient | None = None

    @property
    def api(self) -> TrueNASWSClient:
        if self._api is None:
            msg = "API client not initialized"
            raise RuntimeError(msg)
        return self._api

    def on_mount(self) -> None:
        if not self._config.api_key:
            self.push_screen("first_run")
        else:
            self.push_screen("dashboard")
            self.connect_and_subscribe()

    def connect_and_subscribe(self) -> None:
        self._init_worker()

    def action_switch_screen(self, name: str) -> None:
        self.push_screen(name)

    def action_settings(self) -> None:
        self.push_screen("settings")

    def action_logout(self) -> None:
        self._teardown_worker()
        self.connected = False
        self.connection_error = ""
        self.system_info = {}
        self.realtime = {}
        self.pools = []
        self.disks = []
        self.disk_temps = {}
        self.services = []
        self.push_screen("first_run")

    def on_unmount(self) -> None:
        self._teardown_worker()

    @work(exclusive=True)
    async def _init_worker(self) -> None:
        self._api = TrueNASWSClient(self._config)
        try:
            async with self.api:
                await self.api.authenticate()
                self.connected = True
                self.connection_error = ""
                self.notify("Connected to TrueNAS")
                self._subscribe_worker()
                await self._refresh_all()
                self.set_interval(10, self._poll_realtime)
                await asyncio.Future()
        except TrueNASAPIError as exc:
            self.connected = False
            self.connection_error = f"[{exc.code}] {exc.message}"
            logger.exception("API error")
            self.notify(
                f"API error: {exc.message}",
                severity="error",
                timeout=10,
            )
        except Exception as exc:
            self.connected = False
            self.connection_error = str(exc) or "unknown error"
            logger.exception("connection failed")
            self.notify(
                f"Connection failed: {self.connection_error}",
                severity="error",
                timeout=10,
            )

    @work(exclusive=True)
    async def _teardown_worker(self) -> None:
        if self._api and self.api.connected:
            await self.api.disconnect()
        self.connected = False

    @work(name="subscription-listener", group="subscriptions", exclusive=True)
    async def _subscribe_worker(self) -> None:
        collections = [
            "pool.query",
            "disk.query",
            "service.query",
            "reporting.realtime",
        ]
        for collection in collections:
            await self.api.subscribe(collection, self._on_collection_update)
        logger.info("subscribed to %d collections", len(collections))

    def _on_collection_update(self, params: dict[str, Any]) -> None:
        collection = params.get("collection", "")
        msg = params.get("msg", "")
        fields = params.get("fields", {})

        if not fields and msg in ("ADDED", "CHANGED", "REMOVED"):
            self._refresh_collection(collection)
            return

        match collection:
            case "pool.query":
                self._merge_pool(fields, msg)
            case "disk.query":
                self._merge_disk(fields, msg)
            case "service.query":
                self._merge_service(fields, msg)
            case "reporting.realtime":
                self.realtime = {**self.realtime, **fields} if fields else self.realtime

    def _merge_pool(self, fields: dict[str, Any], msg: str) -> None:
        current = list(self.pools)
        if msg == "REMOVED":
            current = [p for p in current if p.get("id") != fields.get("id")]
        else:
            idx = next(
                (i for i, p in enumerate(current) if p.get("id") == fields.get("id")),
                None,
            )
            if idx is not None:
                current[idx] = {**current[idx], **fields}
            else:
                current.append(fields)
        self.pools = current

    def _merge_disk(self, fields: dict[str, Any], msg: str) -> None:
        current = list(self.disks)
        if msg == "REMOVED":
            current = [
                d for d in current if d.get("identifier") != fields.get("identifier")
            ]
        else:
            idx = next(
                (
                    i
                    for i, d in enumerate(current)
                    if d.get("identifier") == fields.get("identifier")
                ),
                None,
            )
            if idx is not None:
                current[idx] = {**current[idx], **fields}
            else:
                current.append(fields)
        self.disks = current

    def _merge_service(self, fields: dict[str, Any], msg: str) -> None:
        current = list(self.services)
        if msg == "REMOVED":
            current = [s for s in current if s.get("id") != fields.get("id")]
        else:
            idx = next(
                (i for i, s in enumerate(current) if s.get("id") == fields.get("id")),
                None,
            )
            if idx is not None:
                current[idx] = {**current[idx], **fields}
            else:
                current.append(fields)
        self.services = current

    @work(name="collection-refresh", group="refresh", exclusive=True)
    async def _refresh_collection(self, collection: str) -> None:
        match collection:
            case "pool.query":
                self.pools = await self.api.pool_query()
            case "disk.query":
                self.disks = await self.api.disk_query()
            case "service.query":
                self.services = await self.api.service_query()
            case "reporting.realtime":
                self.realtime = await self.api.reporting_realtime()

    async def _refresh_all(self) -> None:
        results = await asyncio.gather(
            self.api.system_info(),
            self.api.pool_query(),
            self.api.disk_query(),
            self.api.disk_temperatures(),
            self.api.service_query(),
            return_exceptions=True,
        )
        info, pools, disks, temps, services = results

        if not isinstance(info, Exception):
            self.log(
                f"system_info raw keys: {sorted(info.keys()) if isinstance(info, dict) else type(info).__name__}"
            )
            self.system_info = self._normalize_system_info(info)
        else:
            self.log(f"system_info error: {info}")

        if not isinstance(pools, Exception):
            self.pools = pools if isinstance(pools, list) else []
        if not isinstance(disks, Exception):
            self.disks = disks if isinstance(disks, list) else []
        if not isinstance(temps, Exception):
            self.disk_temps = temps if isinstance(temps, dict) else {}
        if not isinstance(services, Exception):
            self.services = services if isinstance(services, list) else []

    @work(name="realtime-poll", group="realtime", exclusive=True)
    async def _poll_realtime(self) -> None:
        if not self.connected:
            return
        try:
            self.realtime = await self.api.reporting_realtime()
            temps = await self.api.disk_temperatures()
            self.disk_temps = temps
        except Exception:
            logger.debug("realtime poll failed", exc_info=True)

    def action_refresh_data(self) -> None:
        if self.connected:
            self._refresh_all_worker()

    @work(name="full-refresh", group="refresh", exclusive=True)
    async def _refresh_all_worker(self) -> None:
        await self._refresh_all()

    def watch_connected(self, connected: bool) -> None:
        pass

    @staticmethod
    def _normalize_system_info(raw: dict[str, Any]) -> dict[str, Any]:
        out = dict(raw)

        uptime_seconds = raw.get("uptime_seconds")
        if isinstance(uptime_seconds, (int, float)) and uptime_seconds >= 0:
            total = int(uptime_seconds)
            days = total // 86400
            hours = (total % 86400) // 3600
            minutes = (total % 3600) // 60
            out["uptime_str"] = f"{days}d {hours}h {minutes}m"

        return out
