from __future__ import annotations

import asyncio
import logging
from typing import Any

from textual import work
from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import Footer, Header, Static

from .api import TrueNASWSClient
from .config import ScaleConfig, load_config

logger = logging.getLogger(__name__)


class ScaleApp(App[None]):
    CSS_PATH = "tui.css"
    TITLE = "scale-cli"
    SUB_TITLE = "TrueNAS Scale TUI"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Dark mode"),
        ("r", "refresh_data", "Refresh"),
    ]

    connected: reactive[bool] = reactive(False)
    system_info: reactive[dict[str, Any]] = reactive(dict)
    device_info: reactive[dict[str, Any]] = reactive(dict)
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

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="status")
        yield Footer()

    def on_mount(self) -> None:
        self._init_worker()

    def on_unmount(self) -> None:
        self._teardown_worker()

    @work(exclusive=True)
    async def _init_worker(self) -> None:
        self._api = TrueNASWSClient(self._config)
        try:
            async with self.api:
                await self.api.authenticate()
                self.connected = True
                self._update_status("connected")
                self._subscribe_worker()
                await self._refresh_all()
                await asyncio.sleep_forever()
        except Exception as exc:
            self.connected = False
            self._update_status(f"connection error: {exc}")
            logger.exception("connection failed")

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
            self.api.device_info(),
            self.api.pool_query(),
            self.api.disk_query(),
            self.api.disk_temperatures(),
            self.api.service_query(),
            return_exceptions=True,
        )
        info, dev, pools, disks, temps, services = results

        if not isinstance(info, Exception):
            self.system_info = info
        if not isinstance(dev, Exception):
            self.device_info = dev
        if not isinstance(pools, Exception):
            self.pools = pools
        if not isinstance(disks, Exception):
            self.disks = disks
        if not isinstance(temps, Exception):
            self.disk_temps = temps
        if not isinstance(services, Exception):
            self.services = services

    def action_refresh_data(self) -> None:
        if self.connected:
            self._refresh_all_worker()

    @work(name="full-refresh", group="refresh", exclusive=True)
    async def _refresh_all_worker(self) -> None:
        await self._refresh_all()

    def watch_connected(self, connected: bool) -> None:
        self._update_status("connected" if connected else "disconnected")

    def _update_status(self, text: str) -> None:
        try:
            widget = self.query_one("#status", Static)
            widget.update(text)
        except Exception:
            pass
