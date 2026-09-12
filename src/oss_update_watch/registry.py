from __future__ import annotations

import json
import re
from pathlib import Path


SCHEMA_VERSION = 1
TRACK_MODES = {"auto", "release", "tag", "branch"}
RELATIONS = {"direct", "fork", "reference"}
PRIORITIES = {"high", "normal", "low"}
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def parse_github_repo(value: str) -> str | None:
    value = value.strip().rstrip("/")
    if value.endswith(".git"):
        value = value[:-4]
    if value.startswith("https://github.com/"):
        value = value.removeprefix("https://github.com/")
    elif value.startswith("http://github.com/"):
        value = value.removeprefix("http://github.com/")
    elif value.startswith("git@github.com:"):
        value = value.removeprefix("git@github.com:")
    elif value.startswith("ssh://git@github.com/"):
        value = value.removeprefix("ssh://git@github.com/")
    if not REPO_RE.fullmatch(value):
        return None
    return value


def normalize_repo(value: str) -> str:
    repo = parse_github_repo(value)
    if repo is None:
        raise ValueError(f"Not a GitHub repository: {value}")
    return repo


class Registry:
    def __init__(self, data: dict):
        self.data = data
        self._validate()

    @classmethod
    def empty(cls) -> "Registry":
        return cls({"schema_version": SCHEMA_VERSION, "items": []})

    @classmethod
    def load(cls, path: Path) -> "Registry":
        if not path.exists():
            return cls.empty()
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data.get("items", []):
            item.setdefault("enabled", True)
        return cls(data)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def find(self, repo: str) -> dict | None:
        needle = normalize_repo(repo).casefold()
        return next((item for item in self.data["items"] if item["repo"].casefold() == needle), None)

    def add_usage(
        self,
        repo: str,
        project: str,
        relation: str,
        local_path: str | None,
        *,
        track: str | None = None,
        branch: str | None = None,
        priority: str | None = None,
    ) -> bool:
        repo = normalize_repo(repo)
        project = project.strip()
        if not project:
            raise ValueError("project must not be empty")
        if relation not in RELATIONS:
            raise ValueError(f"relation must be one of: {', '.join(sorted(RELATIONS))}")
        if track is not None and track not in TRACK_MODES:
            raise ValueError(f"track must be one of: {', '.join(sorted(TRACK_MODES))}")
        if priority is not None and priority not in PRIORITIES:
            raise ValueError(f"priority must be one of: {', '.join(sorted(PRIORITIES))}")
        if track == "branch" and not branch:
            raise ValueError("branch tracking requires a branch name")

        item = self.find(repo)
        changed = False
        if item is None:
            selected_track = track or "auto"
            if selected_track == "branch" and not branch:
                raise ValueError("branch tracking requires a branch name")
            item = {
                "repo": repo,
                "enabled": True,
                "tracking": {"mode": selected_track},
                "priority": priority or "normal",
                "usages": [],
            }
            if selected_track == "branch":
                item["tracking"]["branch"] = branch
            self.data["items"].append(item)
            changed = True
        else:
            if track is not None:
                new_tracking = {"mode": track}
                if track == "branch":
                    new_tracking["branch"] = branch
                if item["tracking"] != new_tracking:
                    item["tracking"] = new_tracking
                    changed = True
            if priority is not None and item["priority"] != priority:
                item["priority"] = priority
                changed = True

        usage = next(
            (
                usage
                for usage in item["usages"]
                if usage["project"].casefold() == project.casefold()
            ),
            None,
        )
        if usage is None:
            usage = {"project": project, "relation": relation}
            item["usages"].append(usage)
            changed = True
        elif usage["relation"] != relation:
            usage["relation"] = relation
            changed = True
        if local_path:
            if usage.get("local_path") != local_path:
                usage["local_path"] = local_path
                changed = True

        self.data["items"].sort(key=lambda row: row["repo"].casefold())
        return changed

    def set_enabled(self, repo: str, enabled: bool) -> bool:
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be a boolean")
        item = self.find(repo)
        if item is None:
            raise ValueError(f"Repository is not registered: {normalize_repo(repo)}")
        if item.get("enabled", True) == enabled:
            return False
        item["enabled"] = enabled
        return True

    def remove_usage(self, repo: str, project: str | None = None, *, remove_all: bool = False) -> bool:
        item = self.find(repo)
        if item is None:
            return False
        if remove_all:
            self.data["items"].remove(item)
            return True
        if not project:
            raise ValueError("project is required unless --all is used")

        before = len(item["usages"])
        item["usages"] = [usage for usage in item["usages"] if usage["project"].casefold() != project.casefold()]
        if len(item["usages"]) == before:
            return False
        if not item["usages"]:
            self.data["items"].remove(item)
        return True

    def _validate(self) -> None:
        if self.data.get("schema_version") != SCHEMA_VERSION or not isinstance(self.data.get("items"), list):
            raise ValueError("Unsupported or malformed registry")
        seen: set[str] = set()
        for item in self.data["items"]:
            repo = normalize_repo(item.get("repo", ""))
            key = repo.casefold()
            if key in seen:
                raise ValueError(f"Duplicate repository in registry: {repo}")
            seen.add(key)
            tracking = item.get("tracking", {})
            if tracking.get("mode") not in TRACK_MODES:
                raise ValueError(f"Invalid tracking mode for {repo}")
            if tracking.get("mode") == "branch" and not tracking.get("branch"):
                raise ValueError(f"Branch tracking requires a branch for {repo}")
            if item.get("priority") not in PRIORITIES:
                raise ValueError(f"Invalid priority for {repo}")
            if not isinstance(item.get("enabled", True), bool):
                raise ValueError(f"Invalid enabled state for {repo}")
            if not isinstance(item.get("usages"), list) or not item["usages"]:
                raise ValueError(f"Repository must have at least one usage: {repo}")
            for usage in item["usages"]:
                if not usage.get("project") or usage.get("relation") not in RELATIONS:
                    raise ValueError(f"Invalid usage for {repo}")
