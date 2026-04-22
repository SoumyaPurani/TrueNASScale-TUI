from __future__ import annotations

import asyncio
import json
import logging
import ssl
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection

from .config import ScaleConfig

logger = logging.getLogger(__name__)

_MIDWARE_TIMEOUT = -32603
_BACKOFF_SECONDS = 3.0
_PING_INTERVAL = 20
_PING_TIMEOUT = 30


class TrueNASAPIError(Exception):
    def __init__(self, code: int, message: str, data: Any = None) -> None:
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"[{code}] {message}")


class TrueNASWSClient:
    def __init__(self, config: ScaleConfig) -> None:
        self._config = config
        self._ws: ClientConnection | None = None
        self._id: int = 0
        self._pending: dict[int, asyncio.Future[Any]] = {}
        self._listener_task: asyncio.Task[None] | None = None
        self._sub_callbacks: dict[
            str, list[asyncio.Callable[[dict[str, Any]], Any]]
        ] = {}
        self._connected = asyncio.Event()

    @property
    def connected(self) -> bool:
        return self._connected.is_set()

    async def connect(self) -> None:
        logger.info("connecting to %s", self._config.server_url)
        ssl_ctx: ssl.SSLContext | bool = True
        if not self._config.verify_ssl:
            ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
        self._ws = await websockets.connect(
            self._config.server_url,
            ping_interval=_PING_INTERVAL,
            ping_timeout=_PING_TIMEOUT,
            ssl=ssl_ctx,
        )
        self._listener_task = asyncio.create_task(self._listen())
        self._connected.set()
        logger.info("connected")

    async def authenticate(self) -> None:
        result = await self.call(
            "auth.login_with_api_key", self._config.username, self._config.api_key
        )
        logger.info("authenticated as %s", self._config.username)
        return result

    async def call(self, method: str, *params: Any) -> Any:
        if not self._ws:
            msg = "not connected"
            raise RuntimeError(msg)

        self._id += 1
        rid = self._id
        payload = {
            "jsonrpc": "2.0",
            "id": rid,
            "method": method,
            "params": list(params),
        }

        future: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        self._pending[rid] = future

        await self._ws.send(json.dumps(payload))

        try:
            return await future
        except TrueNASAPIError as exc:
            if exc.code == _MIDWARE_TIMEOUT:
                logger.warning(
                    "middleware timeout on %s, retrying in %ss",
                    method,
                    _BACKOFF_SECONDS,
                )
                await asyncio.sleep(_BACKOFF_SECONDS)
                return await self.call(method, *params)
            raise

    async def subscribe(
        self, event: str, callback: asyncio.Callable[[dict[str, Any]], Any]
    ) -> None:
        await self.call("core.subscribe", event)
        self._sub_callbacks.setdefault(event, []).append(callback)

    async def unsubscribe(self, event: str) -> None:
        await self.call("core.unsubscribe", event)
        self._sub_callbacks.pop(event, None)

    async def disconnect(self) -> None:
        self._connected.clear()
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None

        if self._ws:
            await self._ws.close()
            self._ws = None

        for fut in self._pending.values():
            if not fut.done():
                fut.set_exception(RuntimeError("disconnected"))
        self._pending.clear()
        logger.info("disconnected")

    async def ping(self) -> Any:
        return await self.call("core.ping")

    async def system_info(self) -> dict[str, Any]:
        return await self.call("system.info")

    async def device_info(self) -> dict[str, Any]:
        return await self.call("device.get_info")

    async def reporting_realtime(self) -> dict[str, Any]:
        return await self.call("reporting.realtime")

    async def pool_query(
        self, filters: list[Any] | None = None, options: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        return await self.call("pool.query", filters or [], options or {})

    async def pool_get_instance(self, pool_id: int) -> dict[str, Any]:
        return await self.call("pool.get_instance", pool_id)

    async def pool_scrub_state(self, pool_id: int) -> dict[str, Any]:
        return await self.call("pool.scrub.get_state", pool_id)

    async def disk_query(
        self, filters: list[Any] | None = None, options: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        return await self.call("disk.query", filters or [], options or {})

    async def disk_temperatures(self) -> dict[str, Any]:
        return await self.call("disk.temperatures")

    async def service_query(
        self, filters: list[Any] | None = None, options: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        return await self.call("service.query", filters or [], options or {})

    async def service_control(self, service: str, action: str) -> dict[str, Any]:
        return await self.call(
            "service.control", {"service": service, "action": action}
        )

    async def _listen(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                msg = json.loads(raw)
                if "id" in msg:
                    await self._handle_response(msg)
                elif "method" in msg:
                    await self._handle_notification(msg)
        except websockets.ConnectionClosed:
            logger.warning("connection closed")
            self._connected.clear()
            for fut in self._pending.values():
                if not fut.done():
                    fut.set_exception(RuntimeError("connection lost"))
            self._pending.clear()

    async def _handle_response(self, msg: dict[str, Any]) -> None:
        rid = msg["id"]
        fut = self._pending.pop(rid, None)
        if fut is None or fut.done():
            return

        if "error" in msg:
            err = msg["error"]
            fut.set_exception(
                TrueNASAPIError(
                    code=err.get("code", -1),
                    message=err.get("message", "unknown error"),
                    data=err.get("data"),
                )
            )
        else:
            fut.set_result(msg.get("result"))

    async def _handle_notification(self, msg: dict[str, Any]) -> None:
        method = msg.get("method", "")
        params = msg.get("params", {})

        if method == "collection_update":
            collection = params.get("collection", "")
            for cb in self._sub_callbacks.get(collection, []):
                try:
                    result = cb(params)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception:
                    logger.exception("subscription callback error for %s", collection)

    async def __aenter__(self) -> TrueNASWSClient:
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.disconnect()
