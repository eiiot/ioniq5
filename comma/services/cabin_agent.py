#!/usr/bin/env python3
"""Run cabin USB telemetry and hosted relay synchronization together."""

from __future__ import annotations

import argparse
from pathlib import Path
import threading

import aranet_bridge
import relay_sync


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device")
    parser.add_argument(
        "--latest-path",
        type=Path,
        default=Path(aranet_bridge.DEFAULT_LATEST_PATH),
    )
    parser.add_argument("--server-url", default=relay_sync.DEFAULT_SERVER_URL)
    parser.add_argument(
        "--api-key-path",
        type=Path,
        default=relay_sync.DEFAULT_API_KEY_PATH,
    )
    parser.add_argument(
        "--config-path",
        type=Path,
        default=relay_sync.DEFAULT_CONFIG_PATH,
    )
    parser.add_argument("--interval", type=float, default=15)
    arguments = parser.parse_args()

    usb_thread = threading.Thread(
        name="cabin-usb",
        target=aranet_bridge.run,
        args=(arguments.device, arguments.latest_path),
        daemon=True,
    )
    usb_thread.start()
    relay_sync.run(
        server_url=arguments.server_url,
        api_key_path=arguments.api_key_path,
        config_path=arguments.config_path,
        latest_path=arguments.latest_path,
        interval=arguments.interval,
    )


if __name__ == "__main__":
    main()
