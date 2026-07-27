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
                    "automation": {
                        "enabled": False,
                        "threshold_f": 115.0,
                        "temperature_offset_f": 20.0,
                    },
                    "cabin": None,
                    "connected": False,
                    "climate": {},
                    "last_climate_request": None,
                    "parking": None,
                    "vehicle": None,
                },
            )

            store.patch_config({"enabled": True, "threshold_f": 102})
            store.put_telemetry(
                {"type": "aranet4", "temperature_c": 42.5, "counter": 7},
                received_at_unix=110,
            )
            store.put_telemetry(
                {
                    "type": "sht3x",
                    "temperature_c": 24.5,
                    "humidity_pct": 43.2,
                    "counter": 8,
                },
                received_at_unix=119,
            )
            store.put_telemetry(
                {
                    "type": "sht3x",
                    "temperature_c": 25.0,
                    "humidity_pct": 42.8,
                    "counter": 9,
                    "onroad": False,
                },
                received_at_unix=121,
            )

            status = store.status(now_unix=130)
            self.assertEqual(
                status["automation"],
                {
                    "enabled": True,
                    "threshold_f": 102.0,
                    "temperature_offset_f": 20.0,
                },
            )
            self.assertAlmostEqual(
                status["cabin"]["temperature_c"], 13.8888888889
            )
            self.assertEqual(status["cabin"]["raw_temperature_c"], 25.0)
            self.assertEqual(status["cabin"]["received_at_unix"], 121)
            self.assertTrue(status["connected"])
            self.assertEqual(
                status["parking"],
                {
                    "onroad": False,
                    "parked_at_unix": 121,
                    "protection_eligible_until_unix": 43321,
                },
            )
            self.assertEqual(
                store.history(),
                [
                    {
                        "at_unix": 60,
                        "temperature_c": 13.38888888888889,
                        "raw_temperature_c": 24.5,
                        "humidity_pct": 43.2,
                    },
                    {
                        "at_unix": 120,
                        "temperature_c": 13.88888888888889,
                        "raw_temperature_c": 25.0,
                        "humidity_pct": 42.8,
                    },
                ],
            )

            store.put_vehicle_status(
                {"soc_pct": 21, "source_updated_at": "2026-07-25T23:35:47Z"},
                received_at_unix=121,
            )
            vehicle = store.status(now_unix=122)["vehicle"]
            self.assertEqual(vehicle["soc_pct"], 21)
            self.assertEqual(vehicle["received_at_unix"], 121)

            persisted = json.loads((Path(directory) / "state.json").read_text())
            self.assertEqual(persisted["cabin"]["temperature_c"], 25.0)
            self.assertEqual(persisted["cabin"]["counter"], 9)
            self.assertEqual(len(persisted["cabin_history"]), 2)
            self.assertEqual(persisted["vehicle"]["soc_pct"], 21)
            self.assertEqual(persisted["parking"]["parked_at_unix"], 121)

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
