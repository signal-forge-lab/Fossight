from __future__ import annotations

import subprocess
from pathlib import Path

from .registry import parse_github_repo


def _git_remote(repo_path: Path, name: str) -> str | None:
    result = subprocess.run(
        ["git", "remote", "get-url", name],
        cwd=repo_path,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def discover_repositories(root: Path) -> list[dict]:
    root = root.resolve()
    candidates = [root] if (root / ".git").exists() else [path for path in root.iterdir() if path.is_dir()]
    discovered: list[dict] = []
    for path in sorted(candidates, key=lambda value: value.name.casefold()):
        if not (path / ".git").exists():
            continue
        upstream = parse_github_repo(_git_remote(path, "upstream") or "")
        origin = parse_github_repo(_git_remote(path, "origin") or "")
        tracked = upstream or origin
        if tracked is None:
            continue
        discovered.append(
            {
                "repo": tracked,
                "project": path.name,
                "relation": "fork" if upstream else "direct",
                "local_path": str(path),
            }
        )
    return discovered
