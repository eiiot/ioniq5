#!/usr/bin/env python3
"""Authenticated relay between the mobile app and the comma."""

from __future__ import annotations

import argparse
import hmac
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import subprocess
import threading
import time
from typing import Any

try:
    from server.protection import decide
except ModuleNotFoundError:
    from protection import decide


MAX_REQUEST_BYTES = 16 * 1024
READING_FRESHNESS_SECONDS = 120


class RelayStore:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()

    def _read(self) -> dict[str, Any]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}
        return value if isinstance(value, dict) else {}

    def _write(self, value: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(value, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.path)

    @staticmethod
    def _config(state: dict[str, Any]) -> dict[str, Any]:
        stored = state.get("automation")
        if not isinstance(stored, dict):
            stored = {}
        return {
            "enabled": stored.get("enabled") is True,
            "threshold_f": float(stored.get("threshold_f", 105.0)),
        }

    def config(self) -> dict[str, Any]:
        with self.lock:
            return self._config(self._read())

    def patch_config(self, changes: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            state = self._read()
            config = self._config(state)
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
            state["automation"] = config
            self._write(state)
            return config

    def put_telemetry(
        self, reading: dict[str, Any], received_at_unix: float | None = None
    ) -> dict[str, Any]:
        temperature = reading.get("temperature_c")
        if not isinstance(temperature, (int, float)) or isinstance(
            temperature, bool
        ):
            raise ValueError("temperature_c must be a number")
        cabin = dict(reading)
        cabin["received_at_unix"] = (
            time.time() if received_at_unix is None else received_at_unix
        )
        with self.lock:
            state = self._read()
            state["cabin"] = cabin
            self._write(state)
            return self._config(state)

    def protection_snapshot(self) -> dict[str, Any]:
        with self.lock:
            state = self._read()
            return {
                "automation": self._config(state),
                "cabin": state.get("cabin"),
                "climate": state.get("climate")
                if isinstance(state.get("climate"), dict)
                else {},
            }

    def claim_climate_command(self, action: str, now_unix: float) -> bool:
        with self.lock:
            state = self._read()
            climate = state.get("climate")
            if not isinstance(climate, dict):
                climate = {}
            if climate.get("pending") is not None:
                return False
            climate["pending"] = action
            climate["last_command_at_unix"] = now_unix
            state["climate"] = climate
            self._write(state)
            return True

    def complete_climate_command(
        self,
        action: str,
        succeeded: bool,
        now_unix: float,
        error: str | None = None,
    ) -> None:
        with self.lock:
            state = self._read()
            climate = state.get("climate")
            if not isinstance(climate, dict):
                climate = {}
            climate["pending"] = None
            climate["last_action"] = action
            climate["last_succeeded"] = succeeded
            climate["last_completed_at_unix"] = now_unix
            climate["last_error"] = error
            if succeeded:
                climate["active"] = action == "start"
                if action == "start":
                    climate["started_at_unix"] = now_unix
            state["climate"] = climate
            state["last_climate_request"] = {
                "action": action,
                "succeeded": succeeded,
                "completed_at_unix": now_unix,
                "error": error,
            }
            self._write(state)

    def status(self, now_unix: float | None = None) -> dict[str, Any]:
        now = time.time() if now_unix is None else now_unix
        with self.lock:
            state = self._read()
            cabin = state.get("cabin")
            if not isinstance(cabin, dict):
                cabin = None
            received_at = cabin.get("received_at_unix") if cabin else None
            connected = (
                isinstance(received_at, (int, float))
                and 0 <= now - received_at <= READING_FRESHNESS_SECONDS
            )
            return {
                "automation": self._config(state),
                "cabin": cabin,
                "connected": connected,
                "climate": state.get("climate")
                if isinstance(state.get("climate"), dict)
                else {},
                "last_climate_request": state.get("last_climate_request"),
            }


class ClimateController:
    def __init__(
        self,
        store: RelayStore,
        command: list[str],
        credentials_path: Path,
        commands_enabled: bool,
    ):
        self.store = store
        self.command = command
        self.credentials_path = credentials_path
        self.commands_enabled = commands_enabled

    def evaluate(self, now_unix: float | None = None) -> str | None:
        now = time.time() if now_unix is None else now_unix
        snapshot = self.store.protection_snapshot()
        cabin = snapshot["cabin"]
        if not isinstance(cabin, dict):
            return None
        temperature_c = cabin.get("temperature_c")
        if not isinstance(temperature_c, (int, float)):
            return None
        config = snapshot["automation"]
        action = decide(
            config["enabled"],
            temperature_c * 9 / 5 + 32,
            snapshot["climate"],
            now,
            threshold_f=config["threshold_f"],
        )
        if action is None or not self.commands_enabled:
            return action
        if not self.store.claim_climate_command(action, now):
            return None
        threading.Thread(
            target=self._run,
            args=(action,),
            name=f"bluelink-{action}",
            daemon=True,
        ).start()
        return action

    def _run(self, action: str) -> None:
        try:
            credentials = json.loads(
                self.credentials_path.read_text(encoding="utf-8")
            )
            environment = os.environ.copy()
            environment.update(
                {
                    "BL_USER": credentials["username"],
                    "BL_PASS": credentials["password"],
                    "BL_REGION": credentials["region"],
                }
            )
            completed = subprocess.run(
                [*self.command, action],
                env=environment,
                capture_output=True,
                text=True,
                timeout=90,
                check=False,
            )
            succeeded = completed.returncode == 0
            error = None
            if not succeeded:
                error = (completed.stderr.strip().splitlines() or ["failed"])[-1]
                error = error[:300]
        except (OSError, KeyError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
            succeeded = False
            error = str(exc)[:300]
        self.store.complete_climate_command(
            action, succeeded, time.time(), error
        )


class RelayHandler(BaseHTTPRequestHandler):
    server_version = "ioniq5-relay/1"

    @property
    def app(self) -> "RelayServer":
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

    def authorized(self) -> bool:
        scheme, separator, provided = self.headers.get(
            "Authorization", ""
        ).partition(" ")
        return (
            separator == " "
            and scheme.lower() == "bearer"
            and hmac.compare_digest(provided, self.app.api_key)
        )

    def require_authorization(self) -> bool:
        if self.authorized():
            return True
        self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "Unauthorized"})
        return False

    def read_object(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= MAX_REQUEST_BYTES:
            raise ValueError("Invalid request size")
        value = json.loads(self.rfile.read(length))
        if not isinstance(value, dict):
            raise ValueError("Body must be an object")
        return value

    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_json(HTTPStatus.OK, {"ok": True})
            return
        if not self.require_authorization():
            return
        if self.path == "/v1/status":
            self.send_json(HTTPStatus.OK, self.app.store.status())
            return
        if self.path == "/v1/config":
            self.send_json(
                HTTPStatus.OK, {"automation": self.app.store.config()}
            )
            return
        self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_PATCH(self) -> None:
        if self.path != "/v1/config":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        if not self.require_authorization():
            return
        try:
            self.app.store.patch_config(self.read_object())
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        self.app.controller.evaluate()
        self.send_json(HTTPStatus.OK, self.app.store.status())

    def do_POST(self) -> None:
        if self.path != "/v1/telemetry":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        if not self.require_authorization():
            return
        try:
            config = self.app.store.put_telemetry(self.read_object())
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        self.app.controller.evaluate()
        self.send_json(HTTPStatus.OK, {"automation": config})

    def log_message(self, message_format: str, *arguments: Any) -> None:
        print(
            f"{self.address_string()} - {message_format % arguments}",
            flush=True,
        )


class RelayServer(ThreadingHTTPServer):
    def __init__(
        self,
        address: tuple[str, int],
        api_key: str,
        store: RelayStore,
        controller: ClimateController,
    ):
        super().__init__(address, RelayHandler)
        self.api_key = api_key
        self.store = store
        self.controller = controller


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8790)
    parser.add_argument("--api-key-path", type=Path, required=True)
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--init-api-key", action="store_true")
    parser.add_argument("--bluelink-credentials-path", type=Path, required=True)
    parser.add_argument("--climate-commands-enabled", action="store_true")
    arguments = parser.parse_args()

    if arguments.init_api_key:
        arguments.api_key_path.parent.mkdir(parents=True, exist_ok=True)
        key = secrets.token_urlsafe(32)
        file_descriptor = os.open(
            arguments.api_key_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as key_file:
            key_file.write(key + "\n")
        print("API key created")
        return

    api_key = arguments.api_key_path.read_text(encoding="utf-8").strip()
    if len(api_key) < 32:
        raise SystemExit("API key is missing or too short")
    store = RelayStore(arguments.state_path)
    controller = ClimateController(
        store,
        ["node", str(Path(__file__).with_name("bluelink-cli.cjs"))],
        arguments.bluelink_credentials_path,
        arguments.climate_commands_enabled,
    )
    server = RelayServer(
        (arguments.host, arguments.port),
        api_key,
        store,
        controller,
    )
    print(
        f"relay-api: listening on http://{arguments.host}:{arguments.port}",
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
