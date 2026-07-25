from pathlib import Path
import tempfile
import unittest

from server.relay_api import ClimateController, RelayStore


class ClimateControllerTests(unittest.TestCase):
    def test_disabled_controller_reports_decision_without_running_command(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RelayStore(Path(directory) / "state.json")
            store.patch_config({"enabled": True})
            store.put_telemetry({"temperature_c": 41}, received_at_unix=100)
            controller = ClimateController(
                store, ["should-not-run"], Path(directory) / "credentials.json", False
            )

            self.assertEqual(controller.evaluate(now_unix=101), "start")
            self.assertEqual(store.status(101)["climate"], {})

    def test_command_claim_prevents_duplicate_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RelayStore(Path(directory) / "state.json")

            self.assertTrue(store.claim_climate_command("start", 100))
            self.assertFalse(store.claim_climate_command("start", 101))


if __name__ == "__main__":
    unittest.main()
