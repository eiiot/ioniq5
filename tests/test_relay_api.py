import json
from pathlib import Path
import tempfile
import unittest

from server.relay_api import RelayStore


class RelayStoreTests(unittest.TestCase):
    def test_config_and_telemetry_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RelayStore(Path(directory) / "state.json")

            self.assertEqual(
                store.status(now_unix=100),
                {
                    "automation": {"enabled": False, "threshold_f": 105.0},
                    "cabin": None,
                    "connected": False,
                    "climate": {},
                    "last_climate_request": None,
                    "vehicle": None,
                },
            )

            store.patch_config({"enabled": True, "threshold_f": 102})
            store.put_telemetry(
                {"type": "aranet4", "temperature_c": 42.5, "counter": 7},
                received_at_unix=110,
            )

            status = store.status(now_unix=120)
            self.assertEqual(
                status["automation"],
                {"enabled": True, "threshold_f": 102.0},
            )
            self.assertEqual(status["cabin"]["temperature_c"], 42.5)
            self.assertEqual(status["cabin"]["received_at_unix"], 110)
            self.assertTrue(status["connected"])

            store.put_vehicle_status(
                {"soc_pct": 21, "source_updated_at": "2026-07-25T23:35:47Z"},
                received_at_unix=121,
            )
            vehicle = store.status(now_unix=122)["vehicle"]
            self.assertEqual(vehicle["soc_pct"], 21)
            self.assertEqual(vehicle["received_at_unix"], 121)

            persisted = json.loads((Path(directory) / "state.json").read_text())
            self.assertEqual(persisted["cabin"]["counter"], 7)
            self.assertEqual(persisted["vehicle"]["soc_pct"], 21)

    def test_rejects_invalid_config_and_telemetry(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RelayStore(Path(directory) / "state.json")
            with self.assertRaises(ValueError):
                store.patch_config({"threshold_f": 200})
            with self.assertRaises(ValueError):
                store.put_telemetry({"temperature_c": "hot"}, 100)
            with self.assertRaises(ValueError):
                store.put_vehicle_status({"soc_pct": 101}, 100)


if __name__ == "__main__":
    unittest.main()
