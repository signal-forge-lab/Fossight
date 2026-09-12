"""Deterministic OSS description fallback with offline caching.

Fallback chain (plan section 12):
  1. curated Fossight summary (checked by the caller);
  2. GitHub repository description;
  3. sanitized first useful README paragraph;
  4. "No description available yet."

Remote metadata is cached with timestamps; a stale cache is served while
offline. No LLM or API keys beyond the existing GitHub auth priority.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from .github import GitHubClient, GitHubError


NO_DESCRIPTION = "No description available yet."
CACHE_MAX_AGE_SECONDS = 7 * 24 * 3600
CACHE_SCHEMA_VERSION = 1
SUMMARY_MAX_CHARS = 280

_MARKDOWN_NOISE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)|`{1,3}([^`]*)`{1,3}|\*+|_+|#+\s*")
_WHITESPACE = re.compile(r"\s+")


class MetadataCache:
    """JSON cache of repository summaries with fetch timestamps."""

    def __init__(self, path: Path, max_age_seconds: int = CACHE_MAX_AGE_SECONDS):
        self.path = path
        self.max_age_seconds = max_age_seconds

    def _load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"schema_version": CACHE_SCHEMA_VERSION, "entries": {}}
        if not isinstance(data, dict) or not isinstance(data.get("entries"), dict):
            return {"schema_version": CACHE_SCHEMA_VERSION, "entries": {}}
        return data

    def get(self, repo: str) -> dict | None:
        entry = self._load()["entries"].get(repo)
        if not isinstance(entry, dict) or not isinstance(entry.get("summary"), str):
            return None
        return {
            "summary": entry["summary"],
            "source": entry.get("source", "github"),
            "fetched_at": entry.get("fetched_at"),
            "age_seconds": max(0.0, time.time() - float(entry.get("fetched_at", 0) or 0)),
        }

    def is_fresh(self, entry: dict) -> bool:
        return entry.get("age_seconds", float("inf")) < self.max_age_seconds

    def put(self, repo: str, summary: str, source: str) -> None:
        data = self._load()
        data["schema_version"] = CACHE_SCHEMA_VERSION
        data["entries"][repo] = {
            "summary": summary,
            "source": source,
            "fetched_at": time.time(),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sanitize_summary(text: str, limit: int = SUMMARY_MAX_CHARS) -> str:
    """Collapse markdown/plain text into one clean single-line summary."""
    value = _MARKDOWN_NOISE.sub(lambda m: (m.group(1) or m.group(2) or ""), text or "")
    value = _WHITESPACE.sub(" ", value).strip()
    if len(value) > limit:
        value = value[: limit - 1].rstrip() + "…"
    return value


def readme_first_paragraph(readme_text: str) -> str | None:
    """Extract the first useful paragraph from README text."""
    for block in re.split(r"\n\s*\n", readme_text or ""):
        line = sanitize_summary(block)
        if not line:
            continue
        lowered = line.strip().lower()
        if lowered.startswith(("#", "!", "[!", "<", "|", "---", "===", "badge")):
            continue
        if len(line) < 12:
            continue
        return line
    return None


def describe_repository(
    repo: str,
    client: GitHubClient,
    cache: MetadataCache | None,
) -> dict:
    """Resolve the generic description fallback chain for one repository.

    The curated catalog is consulted by the caller (it is deployment data).
    Returns {"summary", "source", "cached", "fetched_at"}.
    """
    cached = cache.get(repo) if cache else None
    if cached and cache.is_fresh(cached):
        return {
            "summary": cached["summary"],
            "source": cached["source"],
            "cached": True,
            "fetched_at": cached["fetched_at"],
        }

    summary = None
    source = None
    try:
        metadata = client.repository_metadata(repo)
        description = sanitize_summary(metadata.get("description") or "")
        if description:
            summary, source = description, "github"
        if summary is None:
            readme_text = client.repository_readme(repo)
            paragraph = readme_first_paragraph(readme_text or "")
            if paragraph:
                summary, source = paragraph, "readme"
    except GitHubError:
        if cached:
            # Offline (or upstream error): serve the stale cache entry.
            return {
                "summary": cached["summary"],
                "source": cached["source"],
                "cached": True,
                "fetched_at": cached["fetched_at"],
            }
        summary, source = NO_DESCRIPTION, "none"

    if summary is None:
        summary, source = NO_DESCRIPTION, "none"

    if cache is not None and source in {"github", "readme"}:
        cache.put(repo, summary, source)
    return {
        "summary": summary,
        "source": source,
        "cached": False,
        "fetched_at": None,
    }
