import json
import tempfile
import time
import unittest
from pathlib import Path

from oss_update_watch.github import GitHubError
from oss_update_watch.metadata import MetadataCache, NO_DESCRIPTION, describe_repository


class FakeClient:
    def __init__(self, *, description=None, readme=None, error=None):
        self.description = description
        self.readme = readme
        self.error = error
        self.metadata_calls = 0
        self.readme_calls = 0

    def repository_metadata(self, repo):
        self.metadata_calls += 1
        if self.error:
            raise self.error
        return {"description": self.description}

    def repository_readme(self, repo):
        self.readme_calls += 1
        if self.error:
            raise self.error
        return self.readme


class MetadataTests(unittest.TestCase):
    def test_github_description_is_cached_and_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = MetadataCache(Path(tmp) / "metadata.json")
            client = FakeClient(description="A useful repository description")
            first = describe_repository("owner/repo", client, cache)
            self.assertEqual(first["source"], "github")
            self.assertEqual(first["summary"], "A useful repository description")
            self.assertEqual(client.metadata_calls, 1)

            second_client = FakeClient(error=AssertionError("network should not be used"))
            second = describe_repository("owner/repo", second_client, cache)
            self.assertTrue(second["cached"])
            self.assertEqual(second["summary"], first["summary"])
            self.assertEqual(second_client.metadata_calls, 0)

    def test_readme_is_used_when_description_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = MetadataCache(Path(tmp) / "metadata.json")
            client = FakeClient(
                description="",
                readme="# Project\n\nThis **tool** watches repositories and reports changes.\n\nMore text.",
            )
            result = describe_repository("owner/repo", client, cache)
            self.assertEqual(result["source"], "readme")
            self.assertEqual(result["summary"], "This tool watches repositories and reports changes.")

    def test_stale_cache_is_returned_when_github_is_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "metadata.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "entries": {
                            "owner/repo": {
                                "summary": "Previously cached summary",
                                "source": "github",
                                "fetched_at": time.time() - 100,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            cache = MetadataCache(path, max_age_seconds=1)
            client = FakeClient(error=GitHubError("offline"))
            result = describe_repository("owner/repo", client, cache)
            self.assertTrue(result["cached"])
            self.assertEqual(result["summary"], "Previously cached summary")

    def test_no_description_has_deterministic_fallback(self):
        client = FakeClient(description="", readme="")
        result = describe_repository("owner/repo", client, None)
        self.assertEqual(result["source"], "none")
        self.assertEqual(result["summary"], NO_DESCRIPTION)


if __name__ == "__main__":
    unittest.main()
