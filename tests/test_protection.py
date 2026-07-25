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

    def test_command_cooldown_prevents_rapid_restart(self):
        climate = {"active": False, "last_command_at_unix": 900}
        self.assertIsNone(
            decide(True, temperature_f=110, climate=climate, now_unix=1_000)
        )
        self.assertEqual(
            decide(True, temperature_f=110, climate=climate, now_unix=1_501),
            "start",
        )


if __name__ == "__main__":
    unittest.main()
