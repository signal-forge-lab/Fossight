from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request

from . import __version__
from .registry import normalize_repo


class GitHubError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class GitHubClient:
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or self._gh_cli_token()

    @staticmethod
    def _gh_cli_token() -> str | None:
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode != 0:
            return None
        token = result.stdout.strip()
        return token or None

    def latest(self, repo: str, tracking: dict) -> dict:
        repo = normalize_repo(repo)
        mode = tracking["mode"]
        try:
            if mode == "auto":
                return self._latest_auto(repo)
            if mode == "release":
                return self._latest_release(repo)
            if mode == "tag":
                return self._latest_tag(repo)
            if mode == "branch":
                return self._latest_branch(repo, tracking["branch"])
        except (KeyError, IndexError, TypeError) as exc:
            raise GitHubError(f"Unexpected GitHub response for {repo} ({mode})") from exc
        raise GitHubError(f"Unsupported tracking mode: {mode}")

    def _latest_auto(self, repo: str) -> dict:
        try:
            return self._latest_release(repo)
        except GitHubError as exc:
            if exc.status_code != 404:
                raise

        # Confirm the repository itself exists before treating release 404 as
        # "no releases". GitHub also returns 404 for inaccessible repositories.
        metadata = self._request_json(f"repos/{repo}")
        tags = self._request_json(f"repos/{repo}/tags?per_page=1")
        if tags:
            return self._tag_from_payload(repo, tags)
        branch = metadata.get("default_branch")
        if not branch:
            raise GitHubError(f"No release, tag, or default branch found for {repo}")
        return self._latest_branch(repo, branch)

    def _latest_release(self, repo: str) -> dict:
        payload = self._request_json(f"repos/{repo}/releases/latest")
        tag = payload["tag_name"]
        encoded_tag = urllib.parse.quote(tag, safe="")
        commit = self._request_json(f"repos/{repo}/commits/{encoded_tag}")["sha"]
        return {
            "mode": "release",
            "value": tag,
            "commit": commit,
            "ref": f"refs/tags/{tag}",
            "url": payload["html_url"],
            "published_at": payload.get("published_at"),
        }

    def _latest_tag(self, repo: str) -> dict:
        payload = self._request_json(f"repos/{repo}/tags?per_page=1")
        if not payload:
            raise GitHubError(f"No tags found for {repo}")
        return self._tag_from_payload(repo, payload)

    @staticmethod
    def _tag_from_payload(repo: str, payload: list[dict]) -> dict:
        name = payload[0]["name"]
        sha = payload[0]["commit"]["sha"]
        return {
            "mode": "tag",
            "value": f"{name}@{sha}",
            "display": name,
            "commit": sha,
            "ref": f"refs/tags/{name}",
            "url": f"https://github.com/{repo}/tree/{urllib.parse.quote(name, safe='')}",
        }

    def _latest_branch(self, repo: str, branch: str) -> dict:
        encoded_branch = urllib.parse.quote(branch, safe="")
        payload = self._request_json(f"repos/{repo}/branches/{encoded_branch}")
        sha = payload["commit"]["sha"]
        return {
            "mode": "branch",
            "value": sha,
            "display": sha[:12],
            "commit": sha,
            "ref": f"refs/heads/{branch}",
            "url": f"https://github.com/{repo}/commit/{sha}",
            "branch": branch,
        }

    def repository_metadata(self, repo: str) -> dict:
        """Fetch generic repository metadata (description, homepage, ...)."""
        repo = normalize_repo(repo)
        return self._request_json(f"repos/{repo}")

    def repository_readme(self, repo: str) -> str | None:
        """Fetch the raw README text, or None when the repository has none."""
        repo = normalize_repo(repo)
        headers_extra = {"Accept": "application/vnd.github.raw+json"}
        path = f"repos/{repo}/readme"
        headers = {
            "User-Agent": f"oss-update-watch/{__version__}",
            "X-GitHub-Api-Version": "2026-03-10",
            **headers_extra,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(f"https://api.github.com/{path}", headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            rate_hint = ""
            if exc.code == 403 and exc.headers.get("X-RateLimit-Remaining") == "0":
                rate_hint = " (GitHub rate limit reached; provide GITHUB_TOKEN or GH_TOKEN)"
            raise GitHubError(
                f"GitHub HTTP {exc.code} for {path}{rate_hint}", status_code=exc.code
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise GitHubError(f"GitHub request failed for {path}: {exc}") from exc

    def _request_json(self, path: str):
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": f"oss-update-watch/{__version__}",
            "X-GitHub-Api-Version": "2026-03-10",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(f"https://api.github.com/{path}", headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            rate_hint = ""
            if exc.code == 403 and exc.headers.get("X-RateLimit-Remaining") == "0":
                rate_hint = " (GitHub rate limit reached; provide GITHUB_TOKEN or GH_TOKEN)"
            raise GitHubError(
                f"GitHub HTTP {exc.code} for {path}{rate_hint}", status_code=exc.code
            ) from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise GitHubError(f"GitHub request failed for {path}: {exc}") from exc
