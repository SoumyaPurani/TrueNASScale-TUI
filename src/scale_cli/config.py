from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import tomli_w

CONFIG_DIR = Path.home() / ".config" / "scale-cli"
CONFIG_FILE = CONFIG_DIR / "config.toml"

_DEFAULT_HOST = "truenas.local"
_DEFAULT_USERNAME = "admin"
_WS_PATH = "/api/current"


def _host_to_url(host: str) -> str:
    host = host.strip()
    if host.startswith("wss://") or host.startswith("ws://"):
        return host
    return f"wss://{host}{_WS_PATH}"


def _url_to_host(url: str) -> str:
    m = re.match(r"^wss?://([^/]+)", url)
    if m:
        return m.group(1)
    return url


@dataclass
class ScaleConfig:
    server_host: str = _DEFAULT_HOST
    username: str = _DEFAULT_USERNAME
    api_key: str = ""
    verify_ssl: bool = True

    @property
    def server_url(self) -> str:
        return _host_to_url(self.server_host)


def load_config() -> ScaleConfig:
    cfg = ScaleConfig()
    data = {}

    if CONFIG_FILE.exists():
        try:
            import tomllib

            with CONFIG_FILE.open("rb") as f:
                data = tomllib.load(f)
        except Exception:
            data = {}

    server = data.get("server", {})
    raw_url = server.get("url", "")
    if raw_url:
        cfg.server_host = _url_to_host(raw_url)
    raw_host = server.get("host", "")
    if raw_host:
        cfg.server_host = raw_host
    cfg.username = server.get("username", cfg.username)
    cfg.api_key = server.get("api_key", cfg.api_key)
    cfg.verify_ssl = server.get("verify_ssl", cfg.verify_ssl)

    env_server = os.environ.get("TRUENAS_SERVER", "")
    if env_server:
        cfg.server_host = _url_to_host(env_server)
    env_host = os.environ.get("TRUENAS_HOST", "")
    if env_host:
        cfg.server_host = env_host
    cfg.username = os.environ.get("TRUENAS_USERNAME", cfg.username)
    cfg.api_key = os.environ.get("TRUENAS_API_KEY", cfg.api_key)
    cfg.verify_ssl = os.environ.get(
        "TRUENAS_VERIFY_SSL", str(cfg.verify_ssl)
    ).lower() not in (
        "false",
        "0",
        "no",
    )

    return cfg


def save_config(cfg: ScaleConfig) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "server": {
            "host": cfg.server_host,
            "username": cfg.username,
            "api_key": cfg.api_key,
            "verify_ssl": cfg.verify_ssl,
        }
    }
    with CONFIG_FILE.open("wb") as f:
        tomli_w.dump(data, f)
