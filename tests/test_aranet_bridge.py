import importlib.util
import json
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).parents[1] / "comma" / "services" / "aranet_bridge.py"
)
SPEC = importlib.util.spec_from_file_location("aranet_bridge", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ParseReadingTests(unittest.TestCase):
    def test_accepts_aranet4_reading_and_adds_host_timestamp(self):
        payload = {
            "type": "aranet4",
            "address": "c9:ac:87:97:f5:eb",
            "temperature_c": 37.3,
            "co2_ppm": 550,
        }

        parsed = MODULE.parse_reading(json.dumps(payload), received_at=123.5)

        self.assertEqual(parsed["temperature_c"], 37.3)
        self.assertEqual(parsed["received_at_unix"], 123.5)

    def test_accepts_sht41_reading_and_adds_host_timestamp(self):
        payload = {
            "type": "sht41",
            "temperature_c": 24.75,
            "humidity_pct": 43.2,
            "counter": 8,
        }

        parsed = MODULE.parse_reading(json.dumps(payload), received_at=123.5)

        self.assertEqual(parsed["temperature_c"], 24.75)
        self.assertEqual(parsed["humidity_pct"], 43.2)
        self.assertEqual(parsed["received_at_unix"], 123.5)

    def test_ignores_firmware_status_events(self):
        parsed = MODULE.parse_reading(
            '{"event":"scan_complete","aranet_devices":0}', received_at=123.5
        )

        self.assertIsNone(parsed)

    def test_rejects_reading_without_temperature(self):
        parsed = MODULE.parse_reading(
            '{"type":"aranet4","co2_ppm":550}', received_at=123.5
        )

        self.assertIsNone(parsed)

    def test_rejects_invalid_json(self):
        self.assertIsNone(MODULE.parse_reading("not json", received_at=123.5))


if __name__ == "__main__":
    unittest.main()
