# AGENTS.md

## Project overview

TUI for TrueNAS Scale (25.04+) built with Textual. Connects to TrueNAS via **JSON-RPC 2.0 over WebSocket** — not REST. The old `/api/v2.0/` REST API is removed in 25.04+; do not use it.

WebSocket endpoint: `wss://<host>/api/current`

## Commands

```bash
uv run scale-cli          # run the TUI
uv run python -m scale_cli  # alternative entry
uv sync                   # install deps
uv add <pkg>              # add a dependency
uv run ruff check .       # lint (add ruff to dev deps first)
uv run ruff format .      # format
```

There is no test runner or CI yet. Add `pytest` and a `tests/` dir when ready.

## Architecture (planned, not yet built)

```
src/scale_cli/
  __init__.py     # entry point: main()
  app.py          # Textual App class, screen routing, key bindings
  api.py          # WebSocket JSON-RPC 2.0 client (connect, auth, call, reconnect)
  config.py       # read/write ~/.config/scale-cli/config.toml + env var overrides
  screens/        # Textual screens (dashboard, pools, services)
  widgets/        # Reusable Textual widgets (system_info, pool_table, disk_table, service_table)
  tui.css         # Textual CSS
```

**Execution flow**: `main()` → load config → connect WebSocket → authenticate → launch Textual App → screens call `api.py` methods → render in widgets.

## Key constraints

- **Python 3.13+** required (pyproject.toml `requires-python = ">=3.13"`)
- **Build backend**: `uv_build` (not setuptools/hatch). Run `uv sync` after adding deps.
- **WebSocket client**: use the `websockets` library (not httpx WebSocket — httpx WS is experimental and insufficient for JSON-RPC framing)
- **JSON-RPC 2.0** format: `{"jsonrpc":"2.0","id":<int>,"method":"<method>","params":[<args>]}`. Increment `id` per request. Match responses by `id`.
- **Auth flow**: connect to WebSocket → call `auth.login_with_api_key` with username + key → then make authenticated calls. API key format: `{id}-{64-char-string}`.
- **No batch requests** — one JSON-RPC call per WebSocket message.

## Config precedence

1. Environment variables: `TRUENAS_SERVER`, `TRUENAS_API_KEY`, `TRUENAS_USERNAME`
2. Config file: `~/.config/scale-cli/config.toml`
3. Defaults / first-run prompt in TUI

## TrueNAS API methods (v1 scope)

- `system.info` — hostname, version, uptime, load
- `device.get_info` — CPU, memory hardware info
- `reporting.netdata_get_data` — realtime metrics
- `pool.query` / `pool.get_instance` — pool list and details
- `disk.query` / `disk.temperatures` — disk list and temps
- `service.query` / `service.control` — service list and start/stop/restart
- `pool.dataset.query` — dataset listing (post-v1)

## TrueNAS API gotchas

- Query methods accept filters: `[["field","operator","value"]]` as first param, options `{"select":[],"order_by":[]}` as second param.
- Long-running operations (scrub, wipe, pool create) return job IDs. Track via `core.get_jobs`.
- Rate limit: 20 unauthenticated requests per 60s → 10-min cooldown.
- WebSocket must be HTTPS (`wss://`). API keys are revoked if sent over plain `ws://`.
- `auth.login_with_api_key` requires a username parameter (usually `"admin"`).

## Style

- No comments unless asked
- Use `ruff` for lint/format when configured
- Async everywhere — Textual is async-native; all API calls should be `async`
- Use Textual's `set_interval` for periodic data refresh (5-30s), not WebSocket event subscriptions (too complex for v1)

## Planned dependencies

```
textual>=8.2.4
httpx>=0.28.1
websockets>=14.0
tomli-w>=1.0
rich>=13.0
```

Note: `httpx` is kept but not used for the WebSocket connection. The `websockets` library handles that.
