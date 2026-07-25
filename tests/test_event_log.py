import json
from pathlib import Path
import tempfile
import unittest

from server.relay_api import EventLog, RelayStore


class EventLogTests(unittest.TestCase):
    def test_records_config_and_temperature_without_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            store = RelayStore(
                Path(directory) / "state.json",
                EventLog(path),
            )

            store.patch_config({"enabled": True})
            store.put_telemetry({"temperature_c": 42, "counter": 9}, 100)

            records = [
                json.loads(line) for line in path.read_text().splitlines()
            ]
            self.assertEqual(
                [record["event"] for record in records],
                ["config_changed", "temperature_received"],
            )
            self.assertEqual(records[1]["temperature_c"], 42)


if __name__ == "__main__":
    unittest.main()
