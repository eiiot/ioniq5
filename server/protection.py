"""Pure cabin-protection decision logic."""

from __future__ import annotations

from typing import Any, Literal


START_THRESHOLD_F = 105.0
STOP_TARGET_F = 95.0
MINIMUM_RUNTIME_SECONDS = 3 * 60
MAXIMUM_RUNTIME_SECONDS = 10 * 60
COMMAND_COOLDOWN_SECONDS = 10 * 60

Decision = Literal["start", "stop"] | None


def decide(
    enabled: bool,
    temperature_f: float,
    climate: dict[str, Any],
    now_unix: float,
    threshold_f: float = START_THRESHOLD_F,
    target_f: float = STOP_TARGET_F,
) -> Decision:
    active = climate.get("active") is True
    if active:
        if not enabled:
            return "stop"
        started_at = climate.get("started_at_unix")
        if not isinstance(started_at, (int, float)):
            return "stop"
        runtime = now_unix - started_at
        if runtime >= MAXIMUM_RUNTIME_SECONDS:
            return "stop"
        if runtime >= MINIMUM_RUNTIME_SECONDS and temperature_f <= target_f:
            return "stop"
        return None

    if not enabled or temperature_f < threshold_f:
        return None
    last_command_at = climate.get("last_command_at_unix")
    if (
        isinstance(last_command_at, (int, float))
        and now_unix - last_command_at < COMMAND_COOLDOWN_SECONDS
    ):
        return None
    return "start"
