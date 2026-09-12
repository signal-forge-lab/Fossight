import unittest

from oss_update_watch.checker import acknowledge, check_registry, update_status
from oss_update_watch.github import GitHubError


class CheckerTests(unittest.TestCase):
    def test_disabled_repository_is_not_queried(self):
        class FailIfCalledClient:
            def latest(self, repo, tracking):
                raise AssertionError("disabled repository must not call GitHub")

        registry = {
            "items": [
                {
                    "repo": "owner/disabled",
                    "enabled": False,
                    "tracking": {"mode": "release"},
                    "priority": "normal",
                    "usages": [{"project": "tool", "relation": "direct"}],
                }
            ]
        }
        state = {"schema_version": 1, "items": {}}

        report = check_registry(registry, state, FailIfCalledClient())

        self.assertEqual(report["summary"]["disabled"], 1)
        self.assertEqual(report["items"][0]["status"], "disabled")

    def test_unbaselined_when_nothing_has_been_acknowledged(self):
        current = {"mode": "release", "value": "v2.0.0"}
        self.assertEqual(update_status(current, None), "unbaselined")

    def test_up_to_date_when_current_matches_acknowledged(self):
        current = {"mode": "release", "value": "v2.0.0"}
        acknowledged = {"mode": "release", "value": "v2.0.0"}
        self.assertEqual(update_status(current, acknowledged), "up_to_date")

    def test_update_available_when_current_differs_from_acknowledged(self):
        current = {"mode": "release", "value": "v2.1.0"}
        acknowledged = {"mode": "release", "value": "v2.0.0"}
        self.assertEqual(update_status(current, acknowledged), "update_available")

    def test_tracking_mode_change_requires_new_baseline(self):
        current = {"mode": "branch", "value": "abc123"}
        acknowledged = {"mode": "release", "value": "v2.0.0"}
        self.assertEqual(update_status(current, acknowledged), "unbaselined")

    def test_branch_change_requires_new_baseline_even_when_sha_matches(self):
        current = {"mode": "branch", "branch": "develop", "value": "abc123"}
        acknowledged = {"mode": "branch", "branch": "main", "value": "abc123"}
        self.assertEqual(update_status(current, acknowledged), "unbaselined")

    def test_one_github_error_does_not_stop_other_repositories(self):
        class FakeClient:
            def latest(self, repo, tracking):
                if repo == "owner/broken":
                    raise GitHubError("temporary failure")
                return {"mode": "release", "value": "v1.0.0"}

        registry = {
            "items": [
                {
                    "repo": "owner/broken",
                    "tracking": {"mode": "release"},
                    "priority": "high",
                    "usages": [{"project": "a", "relation": "direct"}],
                },
                {
                    "repo": "owner/working",
                    "tracking": {"mode": "release"},
                    "priority": "normal",
                    "usages": [{"project": "b", "relation": "direct"}],
                },
            ]
        }
        state = {"schema_version": 1, "items": {}}

        report = check_registry(registry, state, FakeClient())

        self.assertEqual(report["summary"]["error"], 1)
        self.assertEqual(report["summary"]["unbaselined"], 0)
        self.assertEqual(report["summary"]["up_to_date"], 1)
        self.assertEqual(state["items"]["owner/working"]["acknowledged"]["value"], "v1.0.0")

    def test_first_successful_check_establishes_baseline_automatically(self):
        class FakeClient:
            def latest(self, repo, tracking):
                return {"mode": "release", "value": "v1.0.0"}

        registry = {
            "items": [
                {
                    "repo": "owner/repo",
                    "tracking": {"mode": "release"},
                    "priority": "normal",
                    "usages": [{"project": "tool", "relation": "direct"}],
                }
            ]
        }
        state = {"schema_version": 1, "items": {}}

        report = check_registry(registry, state, FakeClient())

        self.assertEqual(report["summary"]["baseline_pending"], 0)
        self.assertEqual(report["summary"]["upstream_changes"], 0)
        self.assertEqual(state["items"]["owner/repo"]["acknowledged"]["value"], "v1.0.0")

    def test_acknowledge_skips_repository_whose_latest_check_failed(self):
        state = {
            "schema_version": 1,
            "items": {
                "owner/repo": {
                    "observed": {"mode": "release", "value": "v1.0.0"},
                    "acknowledged": {"mode": "release", "value": "v0.9.0"},
                    "error": "temporary failure",
                }
            },
        }

        changed = acknowledge(state, ["owner/repo"])

        self.assertEqual(changed, 0)
        self.assertEqual(state["items"]["owner/repo"]["acknowledged"]["value"], "v0.9.0")


if __name__ == "__main__":
    unittest.main()
