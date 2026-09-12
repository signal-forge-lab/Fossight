"""Prerequisite detection for first-run onboarding.

Detection results never contain secret values: the GitHub auth state reports
only *which* source is active, never the token itself.
"""

from __future__ import annotations

import os
import subprocess


def git_status() -> dict:
    """Detect Git and return its version string without raising."""
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return {"available": False, "version": None}
    if result.returncode != 0:
        return {"available": False, "version": None}
    version = (result.stdout or "").strip() or None
    return {"available": True, "version": version}


def github_auth_source() -> str:
    """Report the active GitHub authentication source, never its value."""
    if os.environ.get("GITHUB_TOKEN"):
        return "GITHUB_TOKEN"
    if os.environ.get("GH_TOKEN"):
        return "GH_TOKEN"
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "anonymous"
    if result.returncode == 0 and result.stdout.strip():
        return "gh_cli"
    return "anonymous"


def prerequisites() -> dict:
    git = git_status()
    source = github_auth_source()
    authenticated = source != "anonymous"
    return {
        "git": git,
        "github_auth": {
            "source": source,
            "authenticated": authenticated,
            "note": (
                None
                if authenticated
                else "Anonymous GitHub API access is rate limited. Fossight works without a token; "
                "set GITHUB_TOKEN or GH_TOKEN if you reach the limit."
            ),
        },
        "remediation": (
            None
            if git["available"]
            else "Git not found. Fossight needs Git to inspect and compare local repositories. "
            "Install Git for Windows from https://git-scm.com/download/win and retry."
        ),
    }
