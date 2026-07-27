import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from comma.services.relay_sync import RelayClient, sync_once


class RelaySyncTests(unittest.TestCase):
    @patch("comma.services.relay_sync.urlopen")
    def test_uses_explicit_user_agent(self, urlopen):
        response = urlopen.return_value.__enter__.return_value
        response.read.return_value = b'{"automation":{"enabled":false}}'
        response.__iter__.return_value = iter(
            [b'{"automation":{"enabled":false}}']
        )

        RelayClient("https://example.test", "secret").get_config()

        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("User-agent"), "ioniq5-comma/1")

    def test_pulls_config_and_pushes_new_telemetry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            latest_path = root / "latest.json"
            config_path = root / "config.json"
            onroad_path = root / "IsOnroad"
            onroad_path.write_text("1")
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
                onroad_path=onroad_path,
            )

            client.get_config.assert_called_once_with()
            client.push_telemetry.assert_called_once()
            self.assertTrue(
                client.push_telemetry.call_args.args[0]["onroad"]
            )
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
                onroad_path=onroad_path,
            )
            self.assertEqual(client.get_config.call_count, 2)
            client.push_telemetry.assert_called_once()

            onroad_path.write_text("0")
            sync_once(
                client,
                latest_path=latest_path,
                config_path=config_path,
                previous_fingerprint=fingerprint,
                onroad_path=onroad_path,
            )
            self.assertEqual(client.push_telemetry.call_count, 2)
            self.assertFalse(
                client.push_telemetry.call_args.args[0]["onroad"]
            )


if __name__ == "__main__":
    unittest.main()
