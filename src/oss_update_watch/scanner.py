"""Local Git repository scanner used by first-run onboarding and re-scan.

The scanner is strictly read-only: it runs ``git remote get-url`` inside
candidate repositories and reports preview rows. It never mutates a
repository, the index, or the worktree.

Quick Scan mirrors the historical ``discover`` behaviour: inspect the root
repository itself, otherwise its direct children only. Deep Scan walks a
selected root recursively with a bounded depth, prunes excluded directory
names, avoids symlink/junction cycles, reports progress, and is cancellable.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .paths import DEFAULT_EXCLUDE_NAMES
from .registry import parse_github_repo


GIT_FILE_NAME = ".git"


class ScanCancelled(RuntimeError):
    """Raised when a caller requests cancellation during a scan."""


@dataclass
class ScanProgress:
    directories_seen: int = 0
    repositories_found: int = 0


@dataclass
class ScanResult:
    rows: list[dict] = field(default_factory=list)
    directories_seen: int = 0
    repositories_found: int = 0
    cancelled: bool = False
    errors: list[dict] = field(default_factory=list)

    def counts(self) -> dict:
        supported = sum(1 for row in self.rows if row["status"] == "ok")
        selected_default = sum(
            1 for row in self.rows if row["status"] == "ok" and not row["already_registered"]
        )
        return {
            "repositories_found": self.repositories_found,
            "supported": supported,
            "skipped": len(self.rows) - supported,
            "new": selected_default,
            "directories_seen": self.directories_seen,
            "cancelled": self.cancelled,
        }


def _is_junction(path: Path) -> bool:
    isjunction = getattr(os.path, "isjunction", None)
    return bool(isjunction and isjunction(path))


def _git_remotes(repo_path: Path) -> dict[str, str]:
    """Read origin/upstream URLs with a single Git process.

    Quick Scan can inspect hundreds of repositories, so spawning one process
    per remote name materially affects latency on Windows. ``git config``
    returns both relevant URLs in one call while preserving the exact remote
    semantics used by the previous implementation.
    """
    try:
        result = subprocess.run(
            ["git", "config", "--get-regexp", r"^remote\.(upstream|origin)\.url$"],
            cwd=repo_path,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            timeout=30.0,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    remotes: dict[str, str] = {}
    for line in result.stdout.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) != 2:
            continue
        key, value = parts
        if not key.startswith("remote.") or not key.endswith(".url"):
            continue
        name = key[len("remote.") : -len(".url")]
        if name in {"upstream", "origin"} and value:
            remotes[name] = value
    return remotes


def is_repository(path: Path) -> bool:
    """Return whether path has a structurally valid Git worktree marker.

    An empty or stale .git entry must not stop Deep Scan from descending
    into child repositories.
    """
    marker = path / GIT_FILE_NAME
    if marker.is_dir():
        return (marker / "HEAD").is_file()
    if not marker.is_file():
        return False
    try:
        text = marker.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return False
    if not text.lower().startswith("gitdir:"):
        return False
    target_text = text.split(":", 1)[1].strip()
    if not target_text:
        return False
    target = Path(target_text)
    if not target.is_absolute():
        target = (path / target).resolve()
    return target.is_dir() and (target / "HEAD").is_file()


def inspect_repository(path: Path, registered: set[str] | None = None) -> dict:
    """Build one preview row for a repository directory.

    Result semantics (plan section 9.3):
      valid GitHub upstream -> track upstream, relation "fork";
      else valid GitHub origin -> track origin, relation "direct";
      else -> skipped with a reason.
    """
    remotes = _git_remotes(path)
    upstream = parse_github_repo(remotes.get("upstream", ""))
    origin = parse_github_repo(remotes.get("origin", ""))
    tracked = upstream or origin
    registered_match = bool(
        tracked and registered and tracked.casefold() in registered
    )
    return {
        "project": path.name,
        "local_path": str(path),
        "repo": tracked,
        "relation": "fork" if upstream else ("direct" if origin else None),
        "remote_source": "upstream" if upstream else ("origin" if origin else None),
        "already_registered": registered_match,
        "status": "ok" if tracked else "skipped",
        "reason": None if tracked else "no_github_remote",
    }


def _registered_lookup(registered_repos: list[str] | set[str] | None) -> set[str]:
    if not registered_repos:
        return set()
    return {repo.casefold() for repo in registered_repos}


def quick_scan(
    root: Path,
    *,
    registered_repos: list[str] | set[str] | None = None,
    should_cancel=None,
) -> ScanResult:
    """Scan the root repository itself, otherwise its direct children only."""
    if should_cancel is not None and should_cancel():
        raise ScanCancelled("Scan cancelled before start")
    root = Path(root).resolve()
    registered = _registered_lookup(registered_repos)
    result = ScanResult()
    if root.is_dir() and is_repository(root):
        candidates = [root]
    elif root.is_dir():
        try:
            candidates = sorted(
                (path for path in root.iterdir() if path.is_dir()),
                key=lambda value: value.name.casefold(),
            )
        except OSError:
            result.errors.append({"path": str(root), "reason": "unreadable_directory"})
            return result
    else:
        result.errors.append({"path": str(root), "reason": "missing_directory"})
        return result

    result.directories_seen = len(candidates)
    for candidate in candidates:
        if should_cancel is not None and should_cancel():
            result.cancelled = True
            return result
        if not is_repository(candidate):
            continue
        result.repositories_found += 1
        try:
            result.rows.append(inspect_repository(candidate, registered))
        except OSError as exc:
            result.errors.append({"path": str(candidate), "reason": f"git_error: {exc}"})
    result.rows.sort(key=lambda row: row["project"].casefold())
    return result


def deep_scan(
    root: Path,
    *,
    max_depth: int = 4,
    exclude_names: list[str] | set[str] | None = None,
    registered_repos: list[str] | set[str] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    progress=None,
    progress_every: int = 25,
) -> ScanResult:
    """Recursively scan ``root`` to ``max_depth`` levels.

    Excluded names are pruned before descending; symlinks and junctions are
    never followed (which also breaks cycles); a found repository is reported
    but not descended into. ``progress`` receives a ScanProgress at least
    every ``progress_every`` directories. ``should_cancel`` returning True
    raises ScanCancelled.
    """
    if max_depth < 1:
        raise ValueError("max_depth must be at least 1")
    if should_cancel is not None and should_cancel():
        raise ScanCancelled("Scan cancelled before start")
    root = Path(root).resolve()
    if not root.is_dir():
        result = ScanResult()
        result.errors.append({"path": str(root), "reason": "missing_directory"})
        return result

    excluded = {name.casefold() for name in (exclude_names or DEFAULT_EXCLUDE_NAMES)}
    registered = _registered_lookup(registered_repos)
    result = ScanResult()
    visited: set[str] = set()

    def emit_progress(force: bool = False) -> None:
        if progress is None:
            return
        if force or result.directories_seen % progress_every == 0:
            progress(
                ScanProgress(
                    directories_seen=result.directories_seen,
                    repositories_found=result.repositories_found,
                )
            )

    def visit(directory: Path, depth: int) -> None:
        if should_cancel is not None and should_cancel():
            raise ScanCancelled("Scan cancelled")
        key = os.path.realpath(directory).casefold()
        if key in visited:
            return
        visited.add(key)
        result.directories_seen += 1
        emit_progress()

        repo = is_repository(directory)
        if repo:
            result.repositories_found += 1
            try:
                result.rows.append(inspect_repository(directory, registered))
            except OSError as exc:
                result.errors.append({"path": str(directory), "reason": f"git_error: {exc}"})
            # Do not descend into nested repositories (plan section 9.2).
            return
        if depth >= max_depth:
            return
        try:
            children = sorted(directory.iterdir(), key=lambda value: value.name.casefold())
        except OSError:
            result.errors.append({"path": str(directory), "reason": "unreadable_directory"})
            return
        for child in children:
            try:
                if not child.is_dir():
                    continue
                if child.is_symlink() or _is_junction(child):
                    continue
                if child.name.casefold() in excluded:
                    continue
            except OSError:
                result.errors.append({"path": str(child), "reason": "unreadable_directory"})
                continue
            visit(child, depth + 1)

    try:
        visit(root, 0)
    except ScanCancelled:
        result.cancelled = True
        emit_progress(force=True)
        return result
    emit_progress(force=True)
    result.rows.sort(key=lambda row: row["project"].casefold())
    return result
