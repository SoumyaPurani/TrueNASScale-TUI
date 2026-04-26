# AGENTS.md

## Project overview

TUI for TrueNAS Scale (25.04+) built with Textual. Connects to TrueNAS via **JSON-RPC 2.0 over WebSocket** — not REST. The old `/api/v2.0/` REST API is removed in 25.04+; do not use it.

WebSocket endpoint: `wss://<host>/api/current` (auto-built from host/IP in config).

## Commands

```bash
uv run truenasscale-tui                                        # run the TUI
uv run truenasscale-tui --server 192.168.1.100 --api-key 1-abc...  # with CLI flags
uv run python -m truenasscale_tui                              # alternative entry
uv sync                                                        # install deps
uv add <pkg>                                                   # add a dependency
uv run ruff check .                                            # lint
uv run ruff format .                                           # format
graphify query graphify-out/graph.json <name>                  # search code symbols
```

CLI flags: `--server` (host/IP only), `--username`, `--api-key`, `--no-verify-ssl`. These override config file and env vars.

No test runner or CI yet.

## Architecture

```
src/truenasscale_tui/
  __init__.py          # main() → argparse → ScaleApp(config).run()
  app.py               # ScaleApp(App) — reactive props, workers, subscription listener, screen nav
  api.py               # TrueNASWSClient — WebSocket JSON-RPC 2.0, auth, reconnect
  config.py            # ScaleConfig dataclass, load/save TOML + env var overrides, host→URL builder
  tui.css              # Textual CSS (all widget/screen styles)
  screens/
    dashboard.py       # DashboardScreen — system info + realtime sparklines + summary tables
    storage.py         # StorageScreen — full pool/disk tables, scrub status/actions
    services.py        # ServicesScreen — service list with start/stop/restart
    first_run.py       # FirstRunScreen — setup form when no API key configured
    settings.py        # SettingsScreen — change host, API key, SSL; save & reconnect
  widgets/
    system_info.py     # SystemInfoCard — hostname, version, uptime, CPU, memory
    realtime_metrics.py # RealtimeMetrics — CPU/memory sparkline graphs
    pool_table.py      # PoolSummaryTable — compact pool overview for dashboard
    disk_table.py      # DiskSummaryTable — compact disk overview for dashboard
    service_table.py   # ServiceSummaryTable — compact service overview for dashboard
```

**Execution flow**: `main()` → argparse → `ScaleApp(config)` → `on_mount` → if no API key: `first_run` screen; else: `dashboard` screen + `_init_worker` (async ctx manager: connect WS → authenticate → subscribe → refresh all) → reactive props update UI. Periodic polling (`set_interval` 10s) for realtime metrics as fallback to subscriptions.

**Screen navigation**: Key bindings `1`/`2`/`3` switch between Dashboard, Storage, Services via `push_screen`. `c` opens Settings, `l` logs out (disconnects + returns to first-run).

**Reactive data flow**: Screens use `self.watch(app, attr, callback)` — NOT `app.watch(self, ...)` which watches the screen instead of the app. All watchers also populate widgets immediately on mount with current app state, so data that arrived before the screen mounted is still displayed.

## Key classes

- **`ScaleApp`** (`app.py:22`) — Textual App. Reactive properties: `connected`, `connection_error`, `system_info`, `realtime`, `pools`, `disks`, `disk_temps`, `services`. Workers handle init, teardown, subscriptions. Key bindings `r` refresh, `1`/`2`/`3` screens, `c` settings, `l` logout. `connect_and_subscribe()` is the public entry point for connecting after first-run/settings.
- **`TrueNASWSClient`** (`api.py:30`) — Async context manager. `call()` sends JSON-RPC, matches responses by `id` via futures. `subscribe()`/`unsubscribe()` for `collection_update` events. Auto-retries on middleware timeout (`-32603`) with 3s backoff.
- **`TrueNASAPIError`** (`api.py:22`) — Raised on JSON-RPC error responses. Carries `code`, `message`, `data`.
- **`ScaleConfig`** (`config.py:33`) — Dataclass: `server_host` (IP/hostname), `username`, `api_key`, `verify_ssl`. `server_url` property auto-builds `wss://<host>/api/current`.

## Key constraints

- **Python 3.13+** required
- **Build backend**: `uv_build` (not setuptools/hatch). Run `uv sync` after adding deps.
- **WebSocket client**: `websockets` library (not httpx WS — insufficient for JSON-RPC framing)
- **JSON-RPC 2.0** format: `{"jsonrpc":"2.0","id":<int>,"method":"<method>","params":[<args>]}`. Increment `id` per request. Match responses by `id`.
- **Auth flow**: connect → `auth.login_with_api_key(api_key)` → authenticated calls. API key format: `{id}-{64-char-string}`. Auth takes a single string param (the key), NOT username+key.
- **No batch requests** — one JSON-RPC call per WebSocket message.
- **Self-signed certs**: TrueNAS uses self-signed certs by default. Set `verify_ssl = false` in config or `TRUENAS_VERIFY_SSL=false` env var. `api.py` creates a permissive `ssl.SSLContext` when disabled.
- **Reactive watchers**: Always use `self.watch(app, attr, callback)` — NOT `app.watch(self, ...)` which watches the wrong object. Never rely on `on_app_*_changed` message handlers (they require `on_scale_app_*` naming which doesn't fire).
- **Init population**: Always call populate/update methods on mount with current app state, so data from before screen mount is visible.

## Config precedence

1. CLI flags: `--server` (host/IP), `--username`, `--api-key`, `--no-verify-ssl`
2. Environment variables: `TRUENAS_SERVER` or `TRUENAS_HOST`, `TRUENAS_API_KEY`, `TRUENAS_USERNAME`, `TRUENAS_VERIFY_SSL`
3. Config file: `~/.config/truenasscale-tui/config.toml`
4. Defaults / first-run prompt in TUI

Config file format:
```toml
[server]
host = "192.168.1.100"
username = "admin"
api_key = "1-abc..."
verify_ssl = false
```

Note: Old config files with `url = "wss://..."` are still supported — the host is extracted on load.

## TrueNAS API methods (v1 scope)

- `system.info` — hostname, version, uptime, load (flat schema in 25.04: `hostname`, `version`, `model`, `cores`, `physmem`, `uptime_seconds`)
- `reporting.realtime` — realtime metrics (preferred over `reporting.netdata_get_data`)
- `pool.query` / `pool.get_instance` / `pool.scrub.get_state` — pool list, details, scrub status
- `disk.query` / `disk.temperatures` — disk list and temps
- `service.query` / `service.control` — service list and start/stop/restart
- `core.subscribe` / `core.unsubscribe` — event subscriptions for `collection_update` notifications
- `core.get_jobs` — track long-running job IDs (scrub, wipe, pool create)

## TrueNAS API gotchas

- Query methods accept filters: `[["field","operator","value"]]` as first param, options `{"select":[],"order_by":[]}` as second param. Only send params when filters/options are non-empty — empty `([], {})` can cause "invalid params".
- Long-running operations return job IDs. Track via `core.get_jobs`.
- Rate limit: 20 unauthenticated requests per 60s → 10-min cooldown.
- WebSocket must be `wss://`. API keys are revoked if sent over plain `ws://`.
- `auth.login_with_api_key` takes a single string parameter (the API key), NOT username+key.
- Error code `-32603` = middleware timeout. `TrueNASWSClient.call()` auto-retries with 3s backoff.
- Error code `-32602` = invalid params. Check param count and types against middleware method signatures.

## Style

- No comments unless asked
- `ruff` for lint/format — run `ruff check --fix . && ruff format .` before committing
- Async everywhere — Textual is async-native; all API calls are `async`
- Textual `@work` decorators for background tasks — never block the event loop
- Use `set_interval` for periodic polling (5-30s) as fallback; `core.subscribe` is preferred for real-time updates

## Dependencies

```
textual>=8.2.4
httpx>=0.28.1
websockets>=16.0
tomli-w>=1.2.0
ruff>=0.15.11 (dev)
```

Note: `httpx` is kept but not used for the WebSocket connection. The `websockets` library handles that.
