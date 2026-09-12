import os
import subprocess
import unittest
from unittest.mock import patch

from oss_update_watch.prereqs import git_status, github_auth_source, prerequisites


class _Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class PrerequisiteTests(unittest.TestCase):
    @patch.dict(os.environ, {"GITHUB_TOKEN": "super-secret-token", "GH_TOKEN": ""}, clear=False)
    def test_auth_source_reports_source_not_secret(self):
        source = github_auth_source()
        self.assertEqual(source, "GITHUB_TOKEN")
        with patch("oss_update_watch.prereqs.git_status", return_value={"available": True, "version": "git version 2"}):
            payload = prerequisites()
        self.assertEqual(payload["github_auth"]["source"], "GITHUB_TOKEN")
        self.assertNotIn("super-secret-token", repr(payload))

    @patch.dict(os.environ, {}, clear=True)
    @patch("oss_update_watch.prereqs.subprocess.run", return_value=_Result(returncode=1))
    def test_anonymous_mode_is_explicit(self, run):
        self.assertEqual(github_auth_source(), "anonymous")

    @patch("oss_update_watch.prereqs.subprocess.run", side_effect=OSError("missing"))
    def test_missing_git_is_actionable_not_exception(self, run):
        self.assertEqual(git_status(), {"available": False, "version": None})
        with patch("oss_update_watch.prereqs.git_status", return_value={"available": False, "version": None}), patch(
            "oss_update_watch.prereqs.github_auth_source", return_value="anonymous"
        ):
            payload = prerequisites()
        self.assertIn("Install Git for Windows", payload["remediation"])


if __name__ == "__main__":
    unittest.main()
