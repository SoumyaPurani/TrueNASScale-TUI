# scale-cli

A terminal user interface for TrueNAS SCALE 25.04+, built with [Textual](https://textual.textualize.io/).

Connects to TrueNAS via **JSON-RPC 2.0 over WebSocket** — the only API available in SCALE 25.04+ (the old REST API has been removed).

## Features

- **Dashboard** — hostname, version, CPU, memory, uptime at a glance; realtime CPU/memory sparkline graphs; pool, disk, and service summary tables
- **Storage** — full pool and disk tables with temperatures; select a pool to view scrub status; start a scrub with one key
- **Services** — service list with running/stopped state and PIDs; start, stop, restart, or toggle services
- **First-run setup** — interactive setup form when no API key is configured
- **Settings** — change server host, API key, or SSL settings at runtime; saves and reconnects automatically
- **Self-signed certs** — SSL verification can be disabled for TrueNAS default certificates
- **Live updates** — realtime metrics via subscription with periodic polling fallback

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- A TrueNAS SCALE 25.04+ server with an API key

## Installation

```bash
git clone https://github.com/SoumyaPurani/scale-cli.git
cd scale-cli
uv sync
```

## Quick Start

```bash
uv run scale-cli
```

On first run with no API key configured, an interactive setup form will appear. Enter your TrueNAS server host/IP and API key to connect.

You can also provide connection details via CLI flags or environment variables:

```bash
uv run scale-cli --server 192.168.1.100 --api-key 1-abc...
```

## CLI Flags

| Flag | Env Variable | Description |
|------|-------------|-------------|
| `--server` | `TRUENAS_SERVER` | TrueNAS host or IP (not a URL) |
| `--username` | `TRUENAS_USERNAME` | Username (informational) |
| `--api-key` | `TRUENAS_API_KEY` | API key (`{id}-{64-char-string}`) |
| `--no-verify-ssl` | `TRUENAS_VERIFY_SSL=false` | Disable SSL verification |

Config precedence: CLI flags > environment variables > config file > defaults.

## Key Bindings

| Key | Action |
|-----|--------|
| `1` | Dashboard |
| `2` | Storage |
| `3` | Services |
| `c` | Settings |
| `l` | Logout (disconnect and return to setup) |
| `r` | Refresh data |
| `d` | Toggle dark mode |
| `q` | Quit |

Storage screen:

| Key | Action |
|-----|--------|
| `s` | Scrub selected pool |
| `Esc` | Back |

Services screen:

| Key | Action |
|-----|--------|
| `Enter` | Toggle selected service |
| `s` | Start selected service |
| `x` | Stop selected service |
| `t` | Restart selected service |
| `Esc` | Back |

## Configuration

### Config file

`~/.config/scale-cli/config.toml`:

```toml
[server]
host = "192.168.1.100"
username = "admin"
api_key = "1-abc..."
verify_ssl = false
```

The `host` field stores the hostname or IP only — the WebSocket URL (`wss://<host>/api/current`) is built automatically.

### Environment variables

```bash
TRUENAS_SERVER=192.168.1.100
TRUENAS_API_KEY=1-abc...
TRUENAS_USERNAME=admin
TRUENAS_VERIFY_SSL=false
uv run scale-cli
```

Environment variables override the config file. CLI flags override everything.

### Getting an API key

1. Open the TrueNAS web UI
2. Navigate to **Credentials > API Keys**
3. Click **Add**
4. Set a name and save — copy the key immediately (it's shown only once)

The API key format is `{id}-{64-character-string}` (e.g. `1-a1b2c3d4...`).

## Architecture

```
src/scale_cli/
├── __init__.py          # entry point (argparse → ScaleApp.run())
├── app.py               # ScaleApp — reactive props, workers, subscriptions
├── api.py               # TrueNASWSClient — WebSocket JSON-RPC 2.0
├── config.py            # ScaleConfig — TOML + env var overrides
├── tui.css              # Textual CSS (all widget/screen styles)
├── screens/
│   ├── dashboard.py     # system info + sparklines + summary tables
│   ├── storage.py       # pool/disk tables, scrub status/actions
│   ├── services.py      # service list with controls
│   ├── first_run.py     # setup form when no API key
│   └── settings.py      # change host/key/SSL, save & reconnect
└── widgets/
    ├── system_info.py       # hostname, version, CPU, memory, uptime
    ├── realtime_metrics.py  # CPU/memory sparkline graphs
    ├── pool_table.py        # compact pool overview
    ├── disk_table.py        # compact disk overview
    └── service_table.py     # compact service overview
```

All API communication uses JSON-RPC 2.0 over `wss://` WebSocket. Auth is via `auth.login_with_api_key` with a single API key parameter. Event subscriptions use `core.subscribe` for live `collection_update` notifications, with 10-second polling as a fallback.

## Development

```bash
uv sync                    # install dependencies
uv run ruff check .        # lint
uv run ruff format .       # format
uv run scale-cli           # run
```

## License

MIT
