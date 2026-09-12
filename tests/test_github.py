import unittest
from unittest.mock import patch

from oss_update_watch.github import GitHubClient, GitHubError


class GitHubClientTests(unittest.TestCase):
    def test_auto_prefers_release(self):
        client = GitHubClient()
        release = {
            "tag_name": "v2.0.0",
            "html_url": "https://github.com/owner/repo/releases/tag/v2.0.0",
            "published_at": "2026-09-01T00:00:00Z",
        }
        with patch.object(client, "_request_json", side_effect=[release, {"sha": "abc123"}]) as request:
            current = client.latest("owner/repo", {"mode": "auto"})

        self.assertEqual(current["mode"], "release")
        self.assertEqual(current["value"], "v2.0.0")
        self.assertEqual(current["commit"], "abc123")
        self.assertEqual(current["ref"], "refs/tags/v2.0.0")
        self.assertEqual(request.call_count, 2)

    def test_auto_falls_back_to_tag_when_repo_has_no_release(self):
        client = GitHubClient()
        responses = [
            GitHubError("not found", status_code=404),
            {"default_branch": "main"},
            [{"name": "v1.4.0", "commit": {"sha": "abc123"}}],
        ]
        with patch.object(client, "_request_json", side_effect=responses):
            current = client.latest("owner/repo", {"mode": "auto"})

        self.assertEqual(current["mode"], "tag")
        self.assertEqual(current["display"], "v1.4.0")

    def test_auto_falls_back_to_default_branch_when_repo_has_no_release_or_tags(self):
        client = GitHubClient()
        responses = [
            GitHubError("not found", status_code=404),
            {"default_branch": "develop"},
            [],
            {"commit": {"sha": "abcdef1234567890"}},
        ]
        with patch.object(client, "_request_json", side_effect=responses):
            current = client.latest("owner/repo", {"mode": "auto"})

        self.assertEqual(current["mode"], "branch")
        self.assertEqual(current["branch"], "develop")
        self.assertEqual(current["display"], "abcdef123456")

    def test_auto_keeps_real_repository_404_as_error(self):
        client = GitHubClient()
        responses = [
            GitHubError("release missing", status_code=404),
            GitHubError("repo missing", status_code=404),
        ]
        with patch.object(client, "_request_json", side_effect=responses):
            with self.assertRaises(GitHubError) as raised:
                client.latest("owner/repo", {"mode": "auto"})

        self.assertEqual(raised.exception.status_code, 404)

    def test_uses_gh_cli_token_when_environment_token_is_absent(self):
        with patch.dict("os.environ", {}, clear=True), patch(
            "oss_update_watch.github.subprocess.run"
        ) as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "secret-token\n"
            client = GitHubClient()

        self.assertEqual(client.token, "secret-token")

    def test_release_uses_latest_stable_release_payload(self):
        client = GitHubClient()
        payload = {
            "tag_name": "v2.0.0",
            "html_url": "https://github.com/owner/repo/releases/tag/v2.0.0",
            "published_at": "2026-09-01T00:00:00Z",
        }
        with patch.object(client, "_request_json", side_effect=[payload, {"sha": "abc123"}]):
            current = client.latest("owner/repo", {"mode": "release"})

        self.assertEqual(current["value"], "v2.0.0")
        self.assertEqual(current["mode"], "release")
        self.assertEqual(current["commit"], "abc123")
        self.assertEqual(current["ref"], "refs/tags/v2.0.0")

    def test_tag_tracks_name_and_commit_sha(self):
        client = GitHubClient()
        payload = [{"name": "v2.0.0", "commit": {"sha": "abc123"}}]
        with patch.object(client, "_request_json", return_value=payload):
            current = client.latest("owner/repo", {"mode": "tag"})

        self.assertEqual(current["value"], "v2.0.0@abc123")
        self.assertEqual(current["display"], "v2.0.0")
        self.assertEqual(current["commit"], "abc123")
        self.assertEqual(current["ref"], "refs/tags/v2.0.0")

    def test_branch_tracks_commit_sha_and_branch_name(self):
        client = GitHubClient()
        payload = {"commit": {"sha": "abcdef1234567890"}}
        with patch.object(client, "_request_json", return_value=payload):
            current = client.latest("owner/repo", {"mode": "branch", "branch": "main"})

        self.assertEqual(current["value"], "abcdef1234567890")
        self.assertEqual(current["display"], "abcdef123456")
        self.assertEqual(current["branch"], "main")
        self.assertEqual(current["commit"], "abcdef1234567890")
        self.assertEqual(current["ref"], "refs/heads/main")


if __name__ == "__main__":
    unittest.main()
