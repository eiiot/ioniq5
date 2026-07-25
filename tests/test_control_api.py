import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = (
    Path(__file__).parents[1] / "comma" / "services" / "control_api.py"
)
SPEC = importlib.util.spec_from_file_location("control_api", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ConfigStoreTests(unittest.TestCase):
    def test_defaults_to_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MODULE.ConfigStore(Path(directory) / "config.json")

            self.assertEqual(
                store.read(), {"enabled": False, "threshold_f": 105.0}
            )

    def test_patch_persists_supported_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            store = MODULE.ConfigStore(path)

            value = store.patch({"enabled": True, "threshold_f": 101})

            self.assertEqual(value, {"enabled": True, "threshold_f": 101.0})
            self.assertEqual(json.loads(path.read_text()), value)

    def test_rejects_invalid_threshold(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MODULE.ConfigStore(Path(directory) / "config.json")

            with self.assertRaises(ValueError):
                store.patch({"threshold_f": 170})


class StatusTests(unittest.TestCase):
    def test_stale_reading_is_not_connected(self):
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            latest_path = directory_path / "latest.json"
            latest_path.write_text(
                json.dumps(
                    {"temperature_c": 35.0, "received_at_unix": 100.0}
                )
            )
            store = MODULE.ConfigStore(directory_path / "config.json")

            status = MODULE.build_status(
                store, latest_path, now_unix=1000.0
            )

            self.assertFalse(status["connected"])
            self.assertEqual(status["cabin"]["temperature_c"], 35.0)


if __name__ == "__main__":
    unittest.main()

