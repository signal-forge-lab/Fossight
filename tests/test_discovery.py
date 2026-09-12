import subprocess
import tempfile
import unittest
from pathlib import Path

from oss_update_watch.discovery import discover_repositories


class DiscoveryTests(unittest.TestCase):
    def test_prefers_upstream_remote_and_marks_fork(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "my-ufo-fork"
            repo.mkdir()
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "remote", "add", "origin", "https://github.com/example/UFO.git"],
                cwd=repo,
                check=True,
            )
            subprocess.run(
                ["git", "remote", "add", "upstream", "https://github.com/microsoft/UFO.git"],
                cwd=repo,
                check=True,
            )

            discovered = discover_repositories(root)

        self.assertEqual(len(discovered), 1)
        self.assertEqual(discovered[0]["repo"], "microsoft/UFO")
        self.assertEqual(discovered[0]["relation"], "fork")
        self.assertEqual(discovered[0]["project"], "my-ufo-fork")


if __name__ == "__main__":
    unittest.main()
