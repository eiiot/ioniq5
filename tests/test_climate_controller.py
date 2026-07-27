from pathlib import Path
import tempfile
import unittest

from server.relay_api import ClimateController, RelayStore


class ClimateControllerTests(unittest.TestCase):
    def test_disabled_controller_reports_decision_without_running_command(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RelayStore(Path(directory) / "state.json")
            store.patch_config({"enabled": True})
            store.put_telemetry({"temperature_c": 52}, received_at_unix=100)
            controller = ClimateController(
                store, ["should-not-run"], Path(directory) / "credentials.json", False
            )

            self.assertEqual(controller.evaluate(now_unix=101), "start")
            self.assertEqual(store.status(101)["climate"], {})

    def test_controller_uses_raw_temperature_for_deciding(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RelayStore(Path(directory) / "state.json")
            store.patch_config({"enabled": True})
            store.put_telemetry({"temperature_c": 46.5}, received_at_unix=100)
            controller = ClimateController(
                store, ["should-not-run"], Path(directory) / "credentials.json", False
            )

            self.assertEqual(controller.evaluate(now_unix=101), "start")

    def test_controller_blocks_start_after_twelve_parked_hours(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RelayStore(Path(directory) / "state.json")
            store.patch_config({"enabled": True})
            store.put_telemetry(
                {"temperature_c": 46.5, "onroad": False},
                received_at_unix=100,
            )
            controller = ClimateController(
                store, ["should-not-run"], Path(directory) / "credentials.json", False
            )

            self.assertEqual(controller.evaluate(now_unix=101), "start")
            self.assertIsNone(
                controller.evaluate(now_unix=100 + 12 * 60 * 60 + 1)
            )

    def test_controller_blocks_start_while_onroad(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RelayStore(Path(directory) / "state.json")
            store.patch_config({"enabled": True})
            store.put_telemetry(
                {"temperature_c": 46.5, "onroad": True},
                received_at_unix=100,
            )
            controller = ClimateController(
                store, ["should-not-run"], Path(directory) / "credentials.json", False
            )

            self.assertIsNone(controller.evaluate(now_unix=101))

    def test_command_claim_prevents_duplicate_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RelayStore(Path(directory) / "state.json")

            self.assertTrue(store.claim_climate_command("start", 100))
            self.assertFalse(store.claim_climate_command("start", 101))


if __name__ == "__main__":
    unittest.main()
