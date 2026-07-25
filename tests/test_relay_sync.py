import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from comma.services.relay_sync import sync_once


class RelaySyncTests(unittest.TestCase):
    def test_pulls_config_and_pushes_new_telemetry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            latest_path = root / "latest.json"
            config_path = root / "config.json"
            latest_path.write_text(
                json.dumps({"temperature_c": 39.2, "counter": 10})
            )
            client = Mock()
            client.get_config.return_value = {
                "enabled": True,
                "threshold_f": 103.0,
            }

            fingerprint = sync_once(
                client,
                latest_path=latest_path,
                config_path=config_path,
                previous_fingerprint=None,
            )

            client.get_config.assert_called_once_with()
            client.push_telemetry.assert_called_once()
            self.assertEqual(
                json.loads(config_path.read_text()),
                {"enabled": True, "threshold_f": 103.0},
            )
            self.assertIsNotNone(fingerprint)

            sync_once(
                client,
                latest_path=latest_path,
                config_path=config_path,
                previous_fingerprint=fingerprint,
            )
            self.assertEqual(client.get_config.call_count, 2)
            client.push_telemetry.assert_called_once()


if __name__ == "__main__":
    unittest.main()
