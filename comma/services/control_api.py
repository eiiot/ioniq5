#!/usr/bin/env python3
"""Authenticated localhost API for IONIQ 5 automation."""

from __future__ import annotations

import argparse
import hmac
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import time
from typing import Any


DEFAULT_API_KEY_PATH = Path("/data/ioniq5/state/control-api.key")
DEFAULT_CONFIG_PATH = Path("/data/ioniq5/state/config.json")
DEFAULT_LATEST_PATH = Path("/tmp/ioniq5/aranet-latest.json")
MAX_REQUEST_BYTES = 8 * 1024
READING_FRESHNESS_SECONDS = 120


class ConfigStore:
    def __init__(self, path: Path):
        self.path = path

    def read(self) -> dict[str, Any]:
        try:
            stored = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            stored = {}
        return {
            "enabled": stored.get("enabled") is True,
            "threshold_f": float(stored.get("threshold_f", 105.0)),
        }

    def patch(self, changes: dict[str, Any]) -> dict[str, Any]:
        config = self.read()
        if "enabled" in changes:
            if not isinstance(changes["enabled"], bool):
                raise ValueError("enabled must be a boolean")
            config["enabled"] = changes["enabled"]
        if "threshold_f" in changes:
            threshold = changes["threshold_f"]
            if (
                not isinstance(threshold, (int, float))
                or isinstance(threshold, bool)
                or not 80 <= threshold <= 130
            ):
                raise ValueError("threshold_f must be between 80 and 130")
            config["threshold_f"] = float(threshold)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps(config, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary_path, self.path)
        return config


def read_latest(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    return value if isinstance(value, dict) else None


def build_status(
    config_store: ConfigStore,
    latest_path: Path,
    now_unix: float | None = None,
) -> dict[str, Any]:
    now = time.time() if now_unix is None else now_unix
    cabin = read_latest(latest_path)
    received_at = cabin.get("received_at_unix") if cabin else None
    connected = (
        isinstance(received_at, (int, float))
        and 0 <= now - received_at <= READING_FRESHNESS_SECONDS
    )
    return {
        "automation": config_store.read(),
        "cabin": cabin,
        "connected": connected,
        "last_climate_request": None,
    }


class ControlApiHandler(BaseHTTPRequestHandler):
    server_version = "ioniq5-control-api/1"

    @property
    def app(self) -> "ControlApiServer":
        return self.server  # type: ignore[return-value]

    def send_json(self, status: HTTPStatus, value: dict[str, Any]) -> None:
        encoded = json.dumps(value, separators=(",", ":")).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(encoded)

    def is_authorized(self) -> bool:
        authorization = self.headers.get("Authorization", "")
        scheme, separator, provided_key = authorization.partition(" ")
        return (
            separator == " "
            and scheme.lower() == "bearer"
            and hmac.compare_digest(provided_key, self.app.api_key)
        )

    def require_authorization(self) -> bool:
        if self.is_authorized():
            return True
        self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "Unauthorized"})
        return False

    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_json(HTTPStatus.OK, {"ok": True})
            return
        if self.path != "/v1/status":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        if not self.require_authorization():
            return
        self.send_json(
            HTTPStatus.OK,
            build_status(self.app.config_store, self.app.latest_path),
        )

    def do_PATCH(self) -> None:
        if self.path != "/v1/config":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        if not self.require_authorization():
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if not 0 < content_length <= MAX_REQUEST_BYTES:
                raise ValueError("Invalid request size")
            changes = json.loads(self.rfile.read(content_length))
            if not isinstance(changes, dict):
                raise ValueError("Body must be an object")
            self.app.config_store.patch(changes)
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return

        self.send_json(
            HTTPStatus.OK,
            build_status(self.app.config_store, self.app.latest_path),
        )

    def log_message(self, message_format: str, *arguments: Any) -> None:
        print(
            f"{self.address_string()} - {message_format % arguments}",
            flush=True,
        )


class ControlApiServer(ThreadingHTTPServer):
    def __init__(
        self,
        address: tuple[str, int],
        api_key: str,
        config_store: ConfigStore,
        latest_path: Path,
    ):
        super().__init__(address, ControlApiHandler)
        self.api_key = api_key
        self.config_store = config_store
        self.latest_path = latest_path


def create_api_key(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    key = secrets.token_urlsafe(32)
    file_descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
    )
    with os.fdopen(file_descriptor, "w", encoding="utf-8") as key_file:
        key_file.write(key + "\n")
    return key


def read_api_key(path: Path) -> str:
    key = path.read_text(encoding="utf-8").strip()
    if len(key) < 32:
        raise ValueError("API key is missing or too short")
    return key


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--api-key-path", type=Path, default=DEFAULT_API_KEY_PATH)
    parser.add_argument("--config-path", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--latest-path", type=Path, default=DEFAULT_LATEST_PATH)
    parser.add_argument("--init-api-key", action="store_true")
    arguments = parser.parse_args()

    if arguments.init_api_key:
        try:
            key = create_api_key(arguments.api_key_path)
        except FileExistsError:
            raise SystemExit(
                f"Refusing to replace existing key: {arguments.api_key_path}"
            )
        print(key)
        return

    try:
        api_key = read_api_key(arguments.api_key_path)
    except (FileNotFoundError, ValueError) as error:
        raise SystemExit(f"{error}. Run with --init-api-key first.")

    server = ControlApiServer(
        (arguments.host, arguments.port),
        api_key,
        ConfigStore(arguments.config_path),
        arguments.latest_path,
    )
    print(
        f"control-api: listening on http://{arguments.host}:{arguments.port}",
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()

