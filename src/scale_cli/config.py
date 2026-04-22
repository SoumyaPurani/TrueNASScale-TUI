from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import tomli_w

CONFIG_DIR = Path.home() / ".config" / "scale-cli"
CONFIG_FILE = CONFIG_DIR / "config.toml"

_DEFAULT_SERVER = "wss://truenas.local/api/current"
_DEFAULT_USERNAME = "admin"


@dataclass
class ScaleConfig:
    server_url: str = _DEFAULT_SERVER
    username: str = _DEFAULT_USERNAME
    api_key: str = ""
    verify_ssl: bool = True


def load_config() -> ScaleConfig:
    cfg = ScaleConfig()

    if CONFIG_FILE.exists():
        try:
            import tomllib

            with CONFIG_FILE.open("rb") as f:
                data = tomllib.load(f)
        except Exception:
            data = {}

        server = data.get("server", {})
        cfg.server_url = server.get("url", cfg.server_url)
        cfg.username = server.get("username", cfg.username)
        cfg.api_key = server.get("api_key", cfg.api_key)
        cfg.verify_ssl = server.get("verify_ssl", cfg.verify_ssl)

    cfg.server_url = os.environ.get("TRUENAS_SERVER", cfg.server_url)
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
            "url": cfg.server_url,
            "username": cfg.username,
            "api_key": cfg.api_key,
            "verify_ssl": cfg.verify_ssl,
        }
    }
    with CONFIG_FILE.open("wb") as f:
        tomli_w.dump(data, f)
