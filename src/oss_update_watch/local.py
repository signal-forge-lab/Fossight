from __future__ import annotations

import subprocess
from pathlib import Path


TEMP_REF = "refs/oss-update-watch/current"


class LocalCheckError(RuntimeError):
    pass


def _git(path: Path, *args: str, timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", "-C", str(path), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise LocalCheckError(str(exc)) from exc


def _output(result: subprocess.CompletedProcess[str], action: str) -> str:
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise LocalCheckError(f"{action} failed" + (f": {detail}" if detail else ""))
    return result.stdout.strip()


def _is_ancestor(path: Path, ancestor: str, descendant: str) -> bool:
    result = _git(path, "merge-base", "--is-ancestor", ancestor, descendant)
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    _output(result, "git merge-base")
    return False


def compare_checkout(path: Path, repo: str, current: dict) -> dict:
    path = path.resolve()
    if not path.is_dir():
        return {"status": "unavailable", "path": str(path), "detail": "Local checkout path is missing"}

    commit = current.get("commit")
    ref = current.get("ref")
    if not commit or not ref:
        return {"status": "unavailable", "path": str(path), "detail": "Upstream commit is unavailable"}

    inside = _git(path, "rev-parse", "--is-inside-work-tree")
    if inside.returncode != 0 or inside.stdout.strip().lower() != "true":
        return {"status": "unavailable", "path": str(path), "detail": "Path is not a Git worktree"}

    head = _output(_git(path, "rev-parse", "HEAD"), "git rev-parse HEAD")
    base = {
        "path": str(path),
        "head": head,
        "upstream_commit": commit,
    }
    if head == commit:
        return {**base, "status": "latest"}

    known = _git(path, "cat-file", "-e", f"{commit}^{{commit}}").returncode == 0
    fetched = False
    try:
        if not known:
            remote = current.get("fetch_url") or f"https://github.com/{repo}.git"
            fetch = _git(
                path,
                "fetch",
                "--quiet",
                "--force",
                "--no-tags",
                "--no-write-fetch-head",
                remote,
                f"{ref}:{TEMP_REF}",
                timeout=60.0,
            )
            _output(fetch, "git fetch upstream ref")
            fetched = True
            fetched_commit = _output(_git(path, "rev-parse", f"{TEMP_REF}^{{commit}}"), "resolve fetched ref")
            if fetched_commit != commit:
                return {
                    **base,
                    "status": "unavailable",
                    "detail": "Upstream changed while the local comparison was running; retry the check",
                }

        if _is_ancestor(path, head, commit):
            return {**base, "status": "behind", "update_available": True}
        if _is_ancestor(path, commit, head):
            return {**base, "status": "ahead"}
        return {**base, "status": "diverged"}
    except LocalCheckError as exc:
        return {**base, "status": "error", "detail": str(exc)}
    finally:
        if fetched:
            _git(path, "update-ref", "-d", TEMP_REF)


def check_local_item(item: dict, current: dict, registry_dir: Path) -> dict:
    usages = []
    for usage in item.get("usages", []):
        value = usage.get("local_path")
        if not value:
            usages.append({**usage, "local": {"status": "unavailable", "detail": "No local checkout path"}})
            continue
        path = Path(value)
        if not path.is_absolute():
            path = registry_dir / path
        usages.append({**usage, "local": compare_checkout(path, item["repo"], current)})

    statuses = [usage["local"]["status"] for usage in usages]
    update_available = any(status == "behind" for status in statuses)
    if any(status == "error" for status in statuses):
        status = "error"
    elif any(status == "diverged" for status in statuses):
        status = "diverged"
    elif update_available:
        status = "behind"
    elif any(status == "ahead" for status in statuses):
        status = "ahead"
    elif statuses and all(status == "latest" for status in statuses):
        status = "latest"
    else:
        status = "unavailable"
    return {"status": status, "update_available": update_available, "usages": usages}
