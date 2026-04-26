from __future__ import annotations

import argparse

from .app import ScaleApp
from .config import ScaleConfig as ScaleConfig, load_config


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="scale-cli",
        description="TUI for TrueNAS SCALE 25.04+",
    )
    parser.add_argument(
        "--server",
        help="TrueNAS host or IP (e.g. 192.168.1.100 or truenas.local)",
    )
    parser.add_argument("--username", help="TrueNAS username (default: admin)")
    parser.add_argument("--api-key", help="TrueNAS API key")
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        help="Disable SSL verification (self-signed certs)",
    )
    args = parser.parse_args()

    try:
        config = load_config()
    except Exception:
        config = ScaleConfig()

    if args.server:
        config.server_host = args.server
    if args.username:
        config.username = args.username
    if args.api_key:
        config.api_key = args.api_key
    if args.no_verify_ssl:
        config.verify_ssl = False

    app = ScaleApp(config=config)
    app.run()
