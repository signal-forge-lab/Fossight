import tempfile
import unittest
from pathlib import Path

from oss_update_watch.registry import Registry, parse_github_repo


class RegistryTests(unittest.TestCase):
    def test_new_entries_are_enabled_by_default(self):
        registry = Registry.empty()
        registry.add_usage("microsoft/UFO", "desktop-control", "direct", None)

        self.assertTrue(registry.data["items"][0]["enabled"])
        self.assertEqual(registry.data["items"][0]["tracking"], {"mode": "auto"})

    def test_legacy_registry_without_enabled_is_loaded_as_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registry.json"
            path.write_text(
                '{"schema_version":1,"items":[{"repo":"owner/repo","tracking":{"mode":"release"},"priority":"normal","usages":[{"project":"tool","relation":"direct"}]}]}',
                encoding="utf-8",
            )

            registry = Registry.load(path)

        self.assertTrue(registry.data["items"][0]["enabled"])

    def test_set_enabled_changes_repository_state(self):
        registry = Registry.empty()
        registry.add_usage("microsoft/UFO", "desktop-control", "direct", None)

        changed = registry.set_enabled("microsoft/UFO", False)

        self.assertTrue(changed)
        self.assertFalse(registry.data["items"][0]["enabled"])

    def test_parse_github_repo_accepts_https_and_ssh(self):
        self.assertEqual(parse_github_repo("https://github.com/microsoft/UFO.git"), "microsoft/UFO")
        self.assertEqual(parse_github_repo("git@github.com:microsoft/UFO.git"), "microsoft/UFO")

    def test_same_repo_can_be_used_by_multiple_projects_without_duplication(self):
        registry = Registry.empty()
        registry.add_usage("microsoft/UFO", "desktop-control", "direct", "../github/UFO")
        registry.add_usage("microsoft/UFO", "research-tool", "reference", None)

        self.assertEqual(len(registry.data["items"]), 1)
        self.assertEqual(len(registry.data["items"][0]["usages"]), 2)

    def test_readding_same_project_updates_relation_instead_of_creating_duplicate_usage(self):
        registry = Registry.empty()
        registry.add_usage("microsoft/UFO", "desktop-control", "direct", "../github/UFO")

        changed = registry.add_usage("microsoft/UFO", "desktop-control", "fork", "../github/UFO")

        self.assertTrue(changed)
        self.assertEqual(len(registry.data["items"][0]["usages"]), 1)
        self.assertEqual(registry.data["items"][0]["usages"][0]["relation"], "fork")

    def test_updating_existing_tracking_or_priority_is_reported_as_change(self):
        registry = Registry.empty()
        registry.add_usage("microsoft/UFO", "desktop-control", "direct", None)

        changed = registry.add_usage(
            "microsoft/UFO",
            "desktop-control",
            "direct",
            None,
            track="branch",
            branch="main",
            priority="high",
        )

        self.assertTrue(changed)
        self.assertEqual(registry.data["items"][0]["tracking"], {"mode": "branch", "branch": "main"})
        self.assertEqual(registry.data["items"][0]["priority"], "high")

    def test_remove_last_usage_removes_unused_source(self):
        registry = Registry.empty()
        registry.add_usage("microsoft/UFO", "desktop-control", "direct", None)

        removed = registry.remove_usage("microsoft/UFO", "desktop-control")

        self.assertTrue(removed)
        self.assertEqual(registry.data["items"], [])

    def test_round_trip_preserves_registry(self):
        registry = Registry.empty()
        registry.add_usage(
            "microsoft/UFO",
            "desktop-control",
            "fork",
            "../github/UFO",
            track="branch",
            branch="main",
            priority="high",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registry.json"
            registry.save(path)
            loaded = Registry.load(path)

        self.assertEqual(loaded.data, registry.data)


if __name__ == "__main__":
    unittest.main()
