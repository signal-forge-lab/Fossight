import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oss_update_watch.cli import main
from oss_update_watch.registry import Registry


class CliTests(unittest.TestCase):
    def test_add_rejects_branch_name_without_branch_tracking(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(SystemExit) as raised:
                main(
                    [
                        "--registry",
                        str(root / "registry.json"),
                        "add",
                        "owner/repo",
                        "--project",
                        "tool",
                        "--branch",
                        "develop",
                    ]
                )

        self.assertEqual(raised.exception.code, 2)

    def test_discover_apply_does_not_overwrite_existing_tracking_or_priority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path = root / "registry.json"
            state_path = root / "state.json"
            reports_path = root / "reports"
            registry = Registry.empty()
            registry.add_usage(
                "owner/repo",
                "existing-tool",
                "reference",
                None,
                track="branch",
                branch="develop",
                priority="high",
            )
            registry.save(registry_path)
            discovered = [
                {
                    "repo": "owner/repo",
                    "project": "new-clone",
                    "relation": "direct",
                    "local_path": str(root / "new-clone"),
                }
            ]

            with patch("oss_update_watch.cli.discover_repositories", return_value=discovered):
                exit_code = main(
                    [
                        "--registry",
                        str(registry_path),
                        "--state",
                        str(state_path),
                        "--reports",
                        str(reports_path),
                        "discover",
                        str(root),
                        "--apply",
                    ]
                )

            loaded = Registry.load(registry_path)

        self.assertEqual(exit_code, 0)
        item = loaded.data["items"][0]
        self.assertEqual(item["tracking"], {"mode": "branch", "branch": "develop"})
        self.assertEqual(item["priority"], "high")
        self.assertEqual(len(item["usages"]), 2)

    def test_discover_defaults_new_repositories_to_auto_tracking(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path = root / "registry.json"
            discovered = [
                {
                    "repo": "owner/repo",
                    "project": "new-clone",
                    "relation": "direct",
                    "local_path": str(root / "new-clone"),
                }
            ]

            with patch("oss_update_watch.cli.discover_repositories", return_value=discovered):
                exit_code = main(["--registry", str(registry_path), "discover", str(root), "--apply"])

            loaded = Registry.load(registry_path)

        self.assertEqual(exit_code, 0)
        self.assertEqual(loaded.data["items"][0]["tracking"], {"mode": "auto"})


if __name__ == "__main__":
    unittest.main()
