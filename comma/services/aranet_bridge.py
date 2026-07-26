#!/usr/bin/env python3
"""Read newline-delimited cabin telemetry from an ESP32-C3 over USB."""

from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path
import select
import sys
import termios
import time
from typing import Any


DEFAULT_DEVICE_GLOB = "/dev/ttyACM*"
DEFAULT_LATEST_PATH = "/tmp/ioniq5/aranet-latest.json"


def parse_reading(line: str, received_at: float) -> dict[str, Any] | None:
    try:
        message = json.loads(line)
    except (json.JSONDecodeError, TypeError):
        return None

    if (
        not isinstance(message, dict)
        or message.get("type") not in {"aranet4", "sht41"}
        or not isinstance(message.get("temperature_c"), (int, float))
    ):
        return None

    message["received_at_unix"] = received_at
    return message


def configure_serial(file_descriptor: int) -> None:
    attributes = termios.tcgetattr(file_descriptor)
    attributes[0] = 0
    attributes[1] = 0
    attributes[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    attributes[3] = 0
    attributes[4] = termios.B115200
    attributes[5] = termios.B115200
    attributes[6][termios.VMIN] = 0
    attributes[6][termios.VTIME] = 10
    termios.tcsetattr(file_descriptor, termios.TCSANOW, attributes)


def write_latest(path: Path, reading: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(reading, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary_path, path)


def resolve_device(explicit_device: str | None) -> str | None:
    if explicit_device:
        return explicit_device if os.path.exists(explicit_device) else None
    devices = sorted(glob.glob(DEFAULT_DEVICE_GLOB))
    return devices[0] if devices else None


def read_device(device: str, latest_path: Path) -> None:
    file_descriptor = os.open(device, os.O_RDONLY | os.O_NOCTTY)
    try:
        configure_serial(file_descriptor)
        buffered = b""
        while True:
            readable, _, _ = select.select([file_descriptor], [], [], 2.0)
            if not readable:
                continue

            chunk = os.read(file_descriptor, 4096)
            if not chunk:
                raise OSError("USB serial device returned EOF")
            buffered += chunk

            while b"\n" in buffered:
                raw_line, buffered = buffered.split(b"\n", 1)
                line = raw_line.decode("utf-8", errors="replace").strip()
                reading = parse_reading(line, received_at=time.time())
                if reading is None:
                    continue
                write_latest(latest_path, reading)
                print(json.dumps(reading, separators=(",", ":")), flush=True)
    finally:
        os.close(file_descriptor)


def run(explicit_device: str | None, latest_path: Path) -> None:
    retry_delay_seconds = 1.0
    while True:
        device = resolve_device(explicit_device)
        if device is None:
            print("aranet-bridge: waiting for /dev/ttyACM*", file=sys.stderr)
            time.sleep(retry_delay_seconds)
            retry_delay_seconds = min(retry_delay_seconds * 2, 15.0)
            continue

        try:
            print(f"aranet-bridge: reading {device}", file=sys.stderr)
            retry_delay_seconds = 1.0
            read_device(device, latest_path)
        except (OSError, termios.error) as error:
            print(f"aranet-bridge: {error}; reconnecting", file=sys.stderr)
            time.sleep(retry_delay_seconds)
            retry_delay_seconds = min(retry_delay_seconds * 2, 15.0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device")
    parser.add_argument(
        "--latest-path", type=Path, default=Path(DEFAULT_LATEST_PATH)
    )
    arguments = parser.parse_args()
    run(arguments.device, arguments.latest_path)


if __name__ == "__main__":
    main()
