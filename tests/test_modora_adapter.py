import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("node"), "Node.js is required for Modora adapter tests")
class ModoraAdapterTests(unittest.TestCase):
    def call_adapter(self, action: str) -> dict:
        request = {
            "protocol": "modora.adapter/v1",
            "moduleId": "oss-update-watch",
            "action": action,
            "context": {"manifestDir": str(ROOT)},
        }
        result = subprocess.run(
            ["node", str(ROOT / "modora-adapter.mjs")],
            input=json.dumps(request),
            text=True,
            capture_output=True,
            check=True,
            timeout=10,
        )
        return json.loads(result.stdout)

    def test_status_reports_registry_counts(self):
        manifest = json.loads((ROOT / "modora.module.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "Fossight")

        response = self.call_adapter("status")
        self.assertTrue(response["ok"])
        self.assertIn(response["state"], {"READY", "RUNNING"})
        signals = {row["id"]: row["value"] for row in response["signals"]}
        registry = json.loads((ROOT / "oss-registry.json").read_text(encoding="utf-8"))
        registered = len(registry["items"])
        enabled = sum(1 for item in registry["items"] if item.get("enabled", True))
        disabled = registered - enabled
        self.assertEqual(signals["registered"], str(registered))
        self.assertEqual(signals["enabled"], str(enabled))
        self.assertEqual(signals["disabled"], str(disabled))


if __name__ == "__main__":
    unittest.main()
