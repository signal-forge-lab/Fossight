import subprocess
import tempfile
import unittest
from pathlib import Path

from oss_update_watch.local import compare_checkout


def git(path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    return result.stdout.strip()


class LocalCheckoutTests(unittest.TestCase):
    def test_detects_latest_behind_ahead_and_diverged_without_touching_worktree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = root / "remote.git"
            seed = root / "seed"
            local = root / "local"
            subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
            subprocess.run(["git", "init", str(seed)], check=True, capture_output=True)
            git(seed, "config", "user.email", "test@example.invalid")
            git(seed, "config", "user.name", "Test")
            (seed / "file.txt").write_text("one\n", encoding="utf-8")
            git(seed, "add", "file.txt")
            git(seed, "commit", "-m", "one")
            git(seed, "branch", "-M", "main")
            git(seed, "remote", "add", "origin", str(remote))
            git(seed, "push", "-u", "origin", "main")
            subprocess.run(["git", "clone", "-b", "main", str(remote), str(local)], check=True, capture_output=True)
            git(local, "config", "user.email", "test@example.invalid")
            git(local, "config", "user.name", "Test")

            first = git(seed, "rev-parse", "HEAD")
            current = {"commit": first, "ref": "refs/heads/main", "fetch_url": str(remote)}
            self.assertEqual(compare_checkout(local, "owner/repo", current)["status"], "latest")

            # Local comparison must remain read-only for dirty and detached
            # worktrees as well as normal branches.
            (local / "dirty.txt").write_text("keep me\n", encoding="utf-8")
            self.assertEqual(compare_checkout(local, "owner/repo", current)["status"], "latest")
            self.assertTrue((local / "dirty.txt").is_file())
            git(local, "checkout", "--detach", first)
            self.assertEqual(compare_checkout(local, "owner/repo", current)["status"], "latest")
            self.assertEqual(git(local, "rev-parse", "--abbrev-ref", "HEAD"), "HEAD")
            git(local, "checkout", "main")

            (seed / "file.txt").write_text("two\n", encoding="utf-8")
            git(seed, "commit", "-am", "two")
            git(seed, "push", "origin", "main")
            second = git(seed, "rev-parse", "HEAD")
            current = {"commit": second, "ref": "refs/heads/main", "fetch_url": str(remote)}
            behind = compare_checkout(local, "owner/repo", current)
            self.assertEqual(behind["status"], "behind")
            self.assertTrue(behind["update_available"])

            git(local, "merge", "--ff-only", second)
            (local / "local.txt").write_text("local\n", encoding="utf-8")
            git(local, "add", "local.txt")
            git(local, "commit", "-m", "local")
            self.assertEqual(compare_checkout(local, "owner/repo", current)["status"], "ahead")

            (seed / "remote.txt").write_text("remote\n", encoding="utf-8")
            git(seed, "add", "remote.txt")
            git(seed, "commit", "-m", "remote")
            git(seed, "push", "origin", "main")
            third = git(seed, "rev-parse", "HEAD")
            current = {"commit": third, "ref": "refs/heads/main", "fetch_url": str(remote)}
            self.assertEqual(compare_checkout(local, "owner/repo", current)["status"], "diverged")

            self.assertFalse((local / ".git" / "refs" / "oss-update-watch" / "current").exists())


if __name__ == "__main__":
    unittest.main()
