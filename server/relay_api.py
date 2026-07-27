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
HISTORY_RETENTION_MINUTES = 24 * 60
DEFAULT_TEMPERATURE_OFFSET_F = 20.0


class EventLog:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()

    def write(self, event: str, **details: Any) -> None:
        record = {
            "at_unix": time.time(),
            "event": event,
            **details,
        }
        encoded = json.dumps(record, separators=(",", ":")) + "\n"
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as output:
                output.write(encoded)


class RelayStore:
    def __init__(self, path: Path, event_log: EventLog | None = None):
        self.path = path
        self.lock = threading.Lock()
        self.event_log = event_log

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
            "temperature_offset_f": float(
                stored.get(
                    "temperature_offset_f", DEFAULT_TEMPERATURE_OFFSET_F
                )
            ),
        }

    @staticmethod
    def _estimated_reading(
        reading: dict[str, Any], temperature_offset_f: float
    ) -> dict[str, Any]:
        estimated = dict(reading)
        temperature_c = reading.get("temperature_c")
        if isinstance(temperature_c, (int, float)) and not isinstance(
            temperature_c, bool
        ):
            estimated["raw_temperature_c"] = float(temperature_c)
            estimated["temperature_c"] = (
                float(temperature_c) - temperature_offset_f / 1.8
            )
        return estimated

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
            if "temperature_offset_f" in changes:
                offset = changes["temperature_offset_f"]
                if (
                    not isinstance(offset, (int, float))
                    or isinstance(offset, bool)
                    or not 0 <= offset <= 50
                ):
                    raise ValueError(
                        "temperature_offset_f must be between 0 and 50"
                    )
                config["temperature_offset_f"] = float(offset)
            state["automation"] = config
            self._write(state)
            if self.event_log is not None:
                self.event_log.write("config_changed", automation=config)
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
            history = state.get("cabin_history")
            if not isinstance(history, list):
                history = []
            minute = int(cabin["received_at_unix"] // 60) * 60
            sample: dict[str, Any] = {
                "at_unix": minute,
                "temperature_c": float(temperature),
            }
            humidity = reading.get("humidity_pct")
            if isinstance(humidity, (int, float)) and not isinstance(
                humidity, bool
            ):
                sample["humidity_pct"] = float(humidity)
            if history and isinstance(history[-1], dict) and history[-1].get(
                "at_unix"
            ) == minute:
                history[-1] = sample
            else:
                history.append(sample)
            oldest_minute = minute - (HISTORY_RETENTION_MINUTES - 1) * 60
            state["cabin_history"] = [
                item
                for item in history
                if isinstance(item, dict)
                and isinstance(item.get("at_unix"), (int, float))
                and item["at_unix"] >= oldest_minute
            ]
            self._write(state)
            if self.event_log is not None:
                self.event_log.write(
                    "temperature_received",
                    temperature_c=temperature,
                    counter=reading.get("counter"),
                    source_recorded_at_unix=reading.get("host_received_at_unix"),
                )
            return self._config(state)

    def history(self) -> list[dict[str, Any]]:
        with self.lock:
            state = self._read()
            history = state.get("cabin_history")
            if not isinstance(history, list):
                return []
            offset = self._config(state)["temperature_offset_f"]
            return [
                self._estimated_reading(item, offset)
                for item in history
                if isinstance(item, dict)
            ]

    def put_vehicle_status(
        self, vehicle: dict[str, Any], received_at_unix: float | None = None
    ) -> None:
        soc = vehicle.get("soc_pct")
        if (
            not isinstance(soc, (int, float))
            or isinstance(soc, bool)
            or not 0 <= soc <= 100
        ):
            raise ValueError("soc_pct must be between 0 and 100")
        stored = dict(vehicle)
        stored["soc_pct"] = int(round(soc))
        stored["received_at_unix"] = (
            time.time() if received_at_unix is None else received_at_unix
        )
        with self.lock:
            state = self._read()
            state["vehicle"] = stored
            self._write(state)
            if self.event_log is not None:
                self.event_log.write(
                    "vehicle_status_received",
                    soc_pct=stored["soc_pct"],
                    source_updated_at=stored.get("source_updated_at"),
                )

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
            if self.event_log is not None:
                self.event_log.write("climate_command_claimed", action=action)
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
            if self.event_log is not None:
                self.event_log.write(
                    "climate_command_completed",
                    action=action,
                    succeeded=succeeded,
                    error=error,
                )

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
                "cabin": (
                    self._estimated_reading(
                        cabin,
                        self._config(state)["temperature_offset_f"],
                    )
                    if cabin is not None
                    else None
                ),
                "connected": connected,
                "climate": state.get("climate")
                if isinstance(state.get("climate"), dict)
                else {},
                "last_climate_request": state.get("last_climate_request"),
                "vehicle": state.get("vehicle")
                if isinstance(state.get("vehicle"), dict)
                else None,
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
        raw_temperature_f = temperature_c * 9 / 5 + 32
        estimated_temperature_f = (
            raw_temperature_f - config["temperature_offset_f"]
        )
        action = decide(
            config["enabled"],
            estimated_temperature_f,
            snapshot["climate"],
            now,
            threshold_f=config["threshold_f"],
        )
        if action is None or not self.commands_enabled:
            return action
        if self.store.event_log is not None:
            self.store.event_log.write(
                "protection_decision",
                action=action,
                temperature_f=estimated_temperature_f,
                raw_temperature_f=raw_temperature_f,
                temperature_offset_f=config["temperature_offset_f"],
                threshold_f=config["threshold_f"],
            )
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
        if self.store.event_log is not None:
            self.store.event_log.write(
                "bluelink_request_started", action=action
            )
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
                    "BL_PIN": credentials["pin"],
                }
            )
            completed = subprocess.run(
                [*self.command, action],
                env=environment,
                capture_output=True,
                text=True,
                timeout=150,
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


class VehicleStatusPoller:
    def __init__(
        self,
        store: RelayStore,
        command: list[str],
        credentials_path: Path,
        interval_seconds: float,
    ):
        self.store = store
        self.command = command
        self.credentials_path = credentials_path
        self.interval_seconds = interval_seconds

    def poll_once(self) -> None:
        credentials = json.loads(
            self.credentials_path.read_text(encoding="utf-8")
        )
        environment = os.environ.copy()
        environment.update(
            {
                "BL_USER": credentials["username"],
                "BL_PASS": credentials["password"],
                "BL_REGION": credentials["region"],
                "BL_PIN": credentials["pin"],
            }
        )
        completed = subprocess.run(
            [*self.command, "status"],
            env=environment,
            capture_output=True,
            text=True,
            timeout=150,
            check=False,
        )
        if completed.returncode != 0:
            error = (completed.stderr.strip().splitlines() or ["failed"])[-1]
            raise RuntimeError(error[:300])
        response = json.loads(completed.stdout)
        result = response.get("result")
        if not isinstance(result, dict):
            raise ValueError("Bluelink status response is missing result")
        self.store.put_vehicle_status(
            {
                "soc_pct": result.get("batteryChargeHV"),
                "source_updated_at": result.get("lastUpdate"),
                "source": "bluelink",
            }
        )

    def run(self) -> None:
        while True:
            try:
                self.poll_once()
            except (
                OSError,
                KeyError,
                ValueError,
                RuntimeError,
                json.JSONDecodeError,
                subprocess.TimeoutExpired,
            ) as error:
                if self.store.event_log is not None:
                    self.store.event_log.write(
                        "vehicle_status_failed", error=str(error)[:300]
                    )
            time.sleep(self.interval_seconds)


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
        if self.path == "/v1/history":
            self.send_json(
                HTTPStatus.OK, {"history": self.app.store.history()}
            )
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
    parser.add_argument("--event-log-path", type=Path)
    parser.add_argument("--climate-commands-enabled", action="store_true")
    parser.add_argument("--vehicle-status-interval", type=float, default=300)
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
    event_log = (
        EventLog(arguments.event_log_path)
        if arguments.event_log_path is not None
        else None
    )
    store = RelayStore(arguments.state_path, event_log)
    controller = ClimateController(
        store,
        ["node", str(Path(__file__).with_name("bluelink-cli.cjs"))],
        arguments.bluelink_credentials_path,
        arguments.climate_commands_enabled,
    )
    vehicle_status_poller = VehicleStatusPoller(
        store,
        ["node", str(Path(__file__).with_name("bluelink-cli.cjs"))],
        arguments.bluelink_credentials_path,
        max(arguments.vehicle_status_interval, 60),
    )
    threading.Thread(
        target=vehicle_status_poller.run,
        name="bluelink-vehicle-status",
        daemon=True,
    ).start()
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
