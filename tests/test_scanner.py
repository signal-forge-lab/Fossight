import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from oss_update_watch.scanner import (
    ScanCancelled,
    deep_scan,
    inspect_repository,
    quick_scan,
)


def git(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(f"git {args} failed: {result.stderr or result.stdout}")
    return result


def make_repo(path: Path, *, origin: str | None = None, upstream: str | None = None) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init")
    git(path, "remote", "add", "origin", origin or "https://github.com/example/placeholder.git")
    if origin is None:
        git(path, "remote", "remove", "origin")
    if upstream:
        git(path, "remote", "add", "upstream", upstream)
    return path


def repository_state(path: Path) -> tuple:
    return (
        git(path, "rev-parse", "HEAD").stdout.strip(),
        git(path, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(),
        git(path, "status", "--porcelain").stdout,
        git(path, "remote", "-v").stdout,
        (path / "tracked.txt").read_bytes(),
    )


class ScannerTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def tearDown(self):
        pass


class QuickScanTests(ScannerTestBase):
    def test_root_repository_is_inspected_when_root_is_a_repo(self):
        repo = make_repo(self.root / "solo", origin="https://github.com/ex/direct.git")
        result = quick_scan(repo)
        self.assertEqual([row["repo"] for row in result.rows], ["ex/direct"])
        self.assertEqual(result.rows[0]["relation"], "direct")
        self.assertEqual(result.rows[0]["remote_source"], "origin")

    def test_quick_scan_inspects_direct_children_only(self):
        make_repo(self.root / "shallow", origin="https://github.com/ex/shallow.git")
        make_repo(self.root / "deep" / "nested", origin="https://github.com/ex/nested.git")
        (self.root / "plain").mkdir()
        result = quick_scan(self.root)
        self.assertEqual([row["project"] for row in result.rows], ["shallow"])
        self.assertEqual(result.repositories_found, 1)
        self.assertEqual(result.directories_seen, 3)

    def test_upstream_wins_and_marks_fork(self):
        make_repo(
            self.root / "forked",
            origin="https://github.com/ex/fork.git",
            upstream="git@github.com:ex/real.git",
        )
        result = quick_scan(self.root)
        row = result.rows[0]
        self.assertEqual(row["repo"], "ex/real")
        self.assertEqual(row["relation"], "fork")
        self.assertEqual(row["remote_source"], "upstream")

    def test_ssh_and_https_remote_forms_are_canonicalized(self):
        make_repo(self.root / "a", origin="git@github.com:Ex/A.git")
        make_repo(self.root / "b", origin="ssh://git@github.com/Ex/A.git")
        make_repo(self.root / "c", origin="https://github.com/Ex/A.git/")
        result = quick_scan(self.root)
        self.assertEqual({row["repo"] for row in result.rows}, {"Ex/A"})

    def test_non_github_and_missing_remotes_are_skipped_with_reason(self):
        make_repo(self.root / "gitlab-only", origin="https://gitlab.com/ex/repo.git")
        make_repo(self.root / "no-remote")
        result = quick_scan(self.root)
        skipped = {row["project"]: row for row in result.rows}
        self.assertEqual(skipped["gitlab-only"]["status"], "skipped")
        self.assertEqual(skipped["gitlab-only"]["reason"], "no_github_remote")
        self.assertIsNone(skipped["no-remote"]["repo"])

    def test_already_registered_is_flagged_from_casefolded_set(self):
        make_repo(self.root / "known", origin="https://github.com/ex/Known.git")
        result = quick_scan(self.root, registered_repos=["EX/known"])
        self.assertTrue(result.rows[0]["already_registered"])

    def test_per_item_git_failure_does_not_abort_the_scan(self):
        make_repo(self.root / "good", origin="https://github.com/ex/good.git")
        make_repo(self.root / "bad", origin="https://github.com/ex/bad.git")
        import oss_update_watch.scanner as scanner

        real_remotes = scanner._git_remotes

        def flaky(path):
            if path.name == "bad":
                raise OSError("git unavailable")
            return real_remotes(path)

        with mock.patch.object(scanner, "_git_remotes", flaky):
            result = scanner.quick_scan(self.root)
        self.assertEqual([row["project"] for row in result.rows], ["good"])


class DeepScanTests(ScannerTestBase):
    def test_deep_scan_ignores_incomplete_root_git_marker_and_descends(self):
        (self.root / ".git").mkdir()
        make_repo(self.root / "nested", origin="https://github.com/ex/nested.git")
        result = deep_scan(self.root, max_depth=2)
        self.assertEqual(result.repositories_found, 1)
        self.assertEqual([row["repo"] for row in result.rows], ["ex/nested"])

    def test_deep_scan_finds_nested_repositories(self):
        make_repo(self.root / "a" / "b" / "repo", origin="https://github.com/ex/nested.git")
        result = deep_scan(self.root, max_depth=4)
        self.assertEqual([row["project"] for row in result.rows], ["repo"])
        self.assertEqual(result.directories_seen > 0, True)

    def test_deep_scan_honors_max_depth(self):
        make_repo(self.root / "a" / "b" / "c" / "d" / "deep-repo", origin="https://github.com/ex/deep.git")
        beyond = deep_scan(self.root, max_depth=4)
        self.assertEqual(beyond.rows, [])
        within = deep_scan(self.root, max_depth=5)
        self.assertEqual([row["repo"] for row in within.rows], ["ex/deep"])

    def test_deep_scan_prunes_excluded_names_and_supports_custom_exclusions(self):
        make_repo(self.root / "node_modules" / "pkg", origin="https://github.com/ex/pkg.git")
        make_repo(self.root / "vendor" / "lib", origin="https://github.com/ex/lib.git")
        make_repo(self.root / "keep", origin="https://github.com/ex/keep.git")
        result = deep_scan(self.root, max_depth=4)
        self.assertEqual([row["project"] for row in result.rows], ["keep"])

        result = deep_scan(self.root, max_depth=4, exclude_names=["vendor"])
        self.assertEqual(sorted(row["project"] for row in result.rows), ["keep", "pkg"])

    def test_deep_scan_reports_progress(self):
        make_repo(self.root / "x" / "repo", origin="https://github.com/ex/x.git")
        events = []
        deep_scan(self.root, max_depth=3, progress=lambda p: events.append(p.repositories_found))
        self.assertTrue(events)
        self.assertEqual(events[-1], 1)

    def test_deep_scan_is_cancellable(self):
        for index in range(3):
            make_repo(self.root / f"r{index}" / "sub", origin=f"https://github.com/ex/r{index}.git")
        state = {"calls": 0}

        def cancel_after_two():
            state["calls"] += 1
            return state["calls"] > 2

        result = deep_scan(self.root, max_depth=3, should_cancel=cancel_after_two)
        self.assertTrue(result.cancelled)

        result = deep_scan(self.root, max_depth=3, should_cancel=lambda: False)
        self.assertFalse(result.cancelled)
        self.assertEqual(len(result.rows), 3)

    def test_deep_scan_never_follows_symlinks_or_junctions(self):
        make_repo(self.root / "real", origin="https://github.com/ex/real.git")
        link = self.root / "loop"
        creation = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(self.root)],
            capture_output=True,
            text=True,
            check=False,
        )
        if creation.returncode != 0:
            self.skipTest(f"junction creation unavailable: {creation.stderr.strip()}")
        result = deep_scan(self.root, max_depth=4)
        projects = [row["project"] for row in result.rows]
        self.assertEqual(projects, ["real"])

    def test_quick_and_deep_scan_leave_repositories_untouched(self):
        repo = make_repo(self.root / "dirty", origin="https://github.com/ex/dirty.git")
        git(repo, "commit", "--allow-empty", "-m", "seed")
        (repo / "tracked.txt").write_text("user edit\n", encoding="utf-8")
        git(repo, "add", ".")
        before = repository_state(repo)

        quick_scan(repo)
        deep_scan(self.root, max_depth=3)

        self.assertEqual(repository_state(repo), before)


class PathHandlingTests(ScannerTestBase):
    def test_spaces_and_japanese_paths_are_supported(self):
        target = self.root / "含む スペース" / "日本語リポジトリ"
        make_repo(target, origin="https://github.com/ex/nihongo.git")
        result = deep_scan(self.root, max_depth=4)
        self.assertEqual([row["project"] for row in result.rows], ["日本語リポジトリ"])
        quick = quick_scan(target)
        self.assertEqual(quick.rows[0]["repo"], "ex/nihongo")

    def test_git_file_checkout_is_accepted(self):
        checkout = self.root / "worktree-style"
        checkout.mkdir()
        metadata = checkout / "elsewhere"
        metadata.mkdir()
        (metadata / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
        (checkout / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
        result = quick_scan(self.root)
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(result.rows[0]["status"], "skipped")

    def test_missing_root_reports_error_not_crash(self):
        result = quick_scan(self.root / "does-not-exist")
        self.assertEqual(result.rows, [])
        self.assertEqual(result.errors[0]["reason"], "missing_directory")
        result = deep_scan(self.root / "does-not-exist")
        self.assertEqual(result.errors[0]["reason"], "missing_directory")

    def test_inspect_repository_skips_malformed_remotes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            row = inspect_repository(repo)
        self.assertEqual(row["status"], "skipped")
        self.assertEqual(row["reason"], "no_github_remote")


if __name__ == "__main__":
    unittest.main()
