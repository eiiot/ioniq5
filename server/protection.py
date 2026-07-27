"""Pure cabin-protection decision logic."""

from __future__ import annotations

from typing import Any, Literal


START_THRESHOLD_F = 105.0
STOP_TARGET_F = 95.0
MINIMUM_RUNTIME_SECONDS = 3 * 60
MAXIMUM_RUNTIME_SECONDS = 10 * 60
RESTART_DELAY_SECONDS = 30
FAILED_START_BACKOFF_SECONDS = 5 * 60
FAILED_STOP_RETRY_SECONDS = 30

Decision = Literal["start", "stop"] | None


def decide(
    enabled: bool,
    temperature_f: float,
    climate: dict[str, Any],
    now_unix: float,
    threshold_f: float = START_THRESHOLD_F,
    target_f: float = STOP_TARGET_F,
    restart_threshold_f: float | None = None,
) -> Decision:
    restart_threshold = (
        threshold_f
        if restart_threshold_f is None
        else restart_threshold_f
    )
    active = climate.get("active") is True
    if active:
        failed_stop = (
            climate.get("last_action") == "stop"
            and climate.get("last_succeeded") is False
            and isinstance(
                climate.get("last_completed_at_unix"), (int, float)
            )
        )
        if (
            failed_stop
            and now_unix - climate["last_completed_at_unix"]
            < FAILED_STOP_RETRY_SECONDS
        ):
            return None
        if not enabled:
            return "stop"
        started_at = climate.get("started_at_unix")
        if not isinstance(started_at, (int, float)):
            return "stop"
        runtime = now_unix - started_at
        if (
            failed_stop
            and runtime >= MAXIMUM_RUNTIME_SECONDS
            and temperature_f >= restart_threshold
        ):
            return "start"
        if runtime >= MAXIMUM_RUNTIME_SECONDS:
            return "stop"
        if runtime >= MINIMUM_RUNTIME_SECONDS and temperature_f <= target_f:
            return "stop"
        return None

    if not enabled:
        return None
    last_completed_at = climate.get("last_completed_at_unix")
    continuing_after_stop = (
        climate.get("last_action") == "stop"
        and climate.get("last_succeeded") is True
        and isinstance(last_completed_at, (int, float))
    )
    if (
        temperature_f < threshold_f
        and not (
            continuing_after_stop
            and temperature_f >= restart_threshold
        )
    ):
        return None
    if (
        continuing_after_stop
        and now_unix - last_completed_at < RESTART_DELAY_SECONDS
    ):
        return None
    if (
        climate.get("last_action") == "start"
        and climate.get("last_succeeded") is False
        and isinstance(last_completed_at, (int, float))
        and now_unix - last_completed_at < FAILED_START_BACKOFF_SECONDS
    ):
        return None
    return "start"
