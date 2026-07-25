import unittest

from server.protection import decide


class ProtectionDecisionTests(unittest.TestCase):
    def test_starts_above_threshold(self):
        self.assertEqual(
            decide(
                enabled=True,
                temperature_f=106,
                climate={},
                now_unix=1_000,
            ),
            "start",
        )

    def test_does_not_start_when_disabled_or_below_threshold(self):
        self.assertIsNone(
            decide(False, temperature_f=110, climate={}, now_unix=1_000)
        )
        self.assertIsNone(
            decide(True, temperature_f=104, climate={}, now_unix=1_000)
        )

    def test_stops_after_cooling_below_target(self):
        climate = {"active": True, "started_at_unix": 1_000}
        self.assertEqual(
            decide(
                True,
                temperature_f=94,
                climate=climate,
                now_unix=1_181,
            ),
            "stop",
        )

    def test_enforces_minimum_runtime_and_maximum_runtime(self):
        climate = {"active": True, "started_at_unix": 1_000}
        self.assertIsNone(
            decide(True, temperature_f=94, climate=climate, now_unix=1_120)
        )
        self.assertEqual(
            decide(True, temperature_f=100, climate=climate, now_unix=1_601),
            "stop",
        )

    def test_stops_active_climate_when_protection_is_disabled(self):
        self.assertEqual(
            decide(
                False,
                temperature_f=100,
                climate={"active": True, "started_at_unix": 1_000},
                now_unix=1_010,
            ),
            "stop",
        )

    def test_restarts_shortly_after_confirmed_stop(self):
        climate = {
            "active": False,
            "last_action": "stop",
            "last_succeeded": True,
            "last_completed_at_unix": 990,
        }
        self.assertIsNone(
            decide(True, temperature_f=110, climate=climate, now_unix=1_000)
        )
        self.assertEqual(
            decide(True, temperature_f=110, climate=climate, now_unix=1_021),
            "start",
        )

    def test_failed_start_uses_longer_backoff(self):
        climate = {
            "active": False,
            "last_action": "start",
            "last_succeeded": False,
            "last_completed_at_unix": 900,
        }
        self.assertIsNone(
            decide(True, temperature_f=110, climate=climate, now_unix=1_000)
        )
        self.assertEqual(
            decide(True, temperature_f=110, climate=climate, now_unix=1_201),
            "start",
        )

    def test_failed_stop_retries_after_short_delay(self):
        climate = {
            "active": True,
            "started_at_unix": 100,
            "last_action": "stop",
            "last_succeeded": False,
            "last_completed_at_unix": 990,
        }
        self.assertIsNone(
            decide(True, temperature_f=110, climate=climate, now_unix=1_000)
        )
        self.assertEqual(
            decide(True, temperature_f=110, climate=climate, now_unix=1_021),
            "stop",
        )


if __name__ == "__main__":
    unittest.main()
