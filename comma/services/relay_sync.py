#!/usr/bin/env python3
"""Synchronize comma telemetry and desired config through the hosted relay."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_API_KEY_PATH = Path("/data/ioniq5/state/control-api.key")
DEFAULT_CONFIG_PATH = Path("/data/ioniq5/state/config.json")
DEFAULT_LATEST_PATH = Path("/tmp/ioniq5/aranet-latest.json")
DEFAULT_ONROAD_PATH = Path("/data/params/d/IsOnroad")
DEFAULT_SERVER_URL = "https://ioniq5-api.tuft.host"


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(value, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


class RelayClient:
    def __init__(self, server_url: str, api_key: str):
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key

    def request(
        self, path: str, method: str = "GET", body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        encoded = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(
            self.server_url + path,
            data=encoded,
            method=method,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "ioniq5-comma/1",
            },
        )
        with urlopen(request, timeout=15) as response:
            return json.load(response)

    def get_config(self) -> dict[str, Any]:
        return self.request("/v1/config")["automation"]

    def push_telemetry(self, reading: dict[str, Any]) -> None:
        self.request("/v1/telemetry", method="POST", body=reading)


def sync_once(
    client: RelayClient,
    latest_path: Path,
    config_path: Path,
    previous_fingerprint: str | None,
    onroad_path: Path = DEFAULT_ONROAD_PATH,
) -> str | None:
    config = client.get_config()
    write_json(config_path, config)

    try:
        raw_reading = latest_path.read_bytes()
        reading = json.loads(raw_reading)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return previous_fingerprint
    if not isinstance(reading, dict):
        return previous_fingerprint

    try:
        onroad_value = onroad_path.read_text(encoding="utf-8").strip()
    except OSError:
        onroad_value = ""
    if onroad_value in {"0", "1"}:
        reading["onroad"] = onroad_value == "1"

    encoded_reading = json.dumps(
        reading, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    fingerprint = hashlib.sha256(encoded_reading).hexdigest()
    if fingerprint != previous_fingerprint:
        client.push_telemetry(reading)
    return fingerprint


def run(
    server_url: str = DEFAULT_SERVER_URL,
    api_key_path: Path = DEFAULT_API_KEY_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
    latest_path: Path = DEFAULT_LATEST_PATH,
    onroad_path: Path = DEFAULT_ONROAD_PATH,
    interval: float = 15,
) -> None:
    api_key = api_key_path.read_text(encoding="utf-8").strip()
    client = RelayClient(server_url, api_key)
    fingerprint = None
    delay = interval
    while True:
        try:
            fingerprint = sync_once(
                client,
                latest_path=latest_path,
                config_path=config_path,
                previous_fingerprint=fingerprint,
                onroad_path=onroad_path,
            )
            delay = interval
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
            print(f"relay-sync: {error}; retrying", flush=True)
            delay = min(max(delay * 2, 5), 60)
        time.sleep(delay)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-url", default=DEFAULT_SERVER_URL)
    parser.add_argument("--api-key-path", type=Path, default=DEFAULT_API_KEY_PATH)
    parser.add_argument("--config-path", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--latest-path", type=Path, default=DEFAULT_LATEST_PATH)
    parser.add_argument("--onroad-path", type=Path, default=DEFAULT_ONROAD_PATH)
    parser.add_argument("--interval", type=float, default=15)
    arguments = parser.parse_args()
    run(
        server_url=arguments.server_url,
        api_key_path=arguments.api_key_path,
        config_path=arguments.config_path,
        latest_path=arguments.latest_path,
        onroad_path=arguments.onroad_path,
        interval=arguments.interval,
    )


if __name__ == "__main__":
    main()
