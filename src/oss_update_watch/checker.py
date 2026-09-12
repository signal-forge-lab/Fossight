from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .github import GitHubClient, GitHubError
from .local import check_local_item


STATE_SCHEMA_VERSION = 1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def update_status(current: dict, acknowledged: dict | None) -> str:
    if acknowledged is None or acknowledged.get("mode") != current.get("mode"):
        return "unbaselined"
    if current.get("mode") == "branch" and acknowledged.get("branch") != current.get("branch"):
        return "unbaselined"
    return "up_to_date" if acknowledged.get("value") == current.get("value") else "update_available"


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": STATE_SCHEMA_VERSION, "items": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != STATE_SCHEMA_VERSION or not isinstance(data.get("items"), dict):
        raise ValueError("Unsupported or malformed state file")
    return data


def save_state(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def check_registry(
    registry: dict,
    state: dict,
    client: GitHubClient | None = None,
    *,
    registry_dir: Path | None = None,
    local_checker=check_local_item,
) -> dict:
    client = client or GitHubClient()
    registry_dir = (registry_dir or Path.cwd()).resolve()
    generated_at = utc_now()
    rows: list[dict] = []
    for item in registry["items"]:
        repo = item["repo"]
        if not item.get("enabled", True):
            rows.append({**item, "status": "disabled"})
            continue
        state_item = state["items"].setdefault(repo, {})
        try:
            current = client.latest(repo, item["tracking"])
            state_item["observed"] = current
            state_item["checked_at"] = generated_at
            state_item.pop("error", None)
            status = update_status(current, state_item.get("acknowledged"))
            if status == "unbaselined":
                state_item["acknowledged"] = current
                state_item["baseline_at"] = generated_at
                status = "up_to_date"
            local = local_checker(item, current, registry_dir)
            state_item["local"] = local
            rows.append(
                {
                    **item,
                    "status": status,
                    "current": current,
                    "acknowledged": state_item.get("acknowledged"),
                    "local": local,
                }
            )
        except GitHubError as exc:  # One upstream failure must not stop the whole watch list.
            state_item["checked_at"] = generated_at
            state_item["error"] = str(exc)
            local = {"status": "unavailable", "update_available": False, "usages": []}
            state_item["local"] = local
            rows.append(
                {
                    **item,
                    "status": "error",
                    "error": str(exc),
                    "acknowledged": state_item.get("acknowledged"),
                    "local": local,
                }
            )

    order = {"update_available": 0, "error": 1, "unbaselined": 2, "up_to_date": 3, "disabled": 4}
    priority = {"high": 0, "normal": 1, "low": 2}
    rows.sort(
        key=lambda row: (
            0 if row.get("local", {}).get("update_available") else 1,
            order[row["status"]],
            priority[row["priority"]],
            row["repo"].casefold(),
        )
    )
    counts = {name: sum(1 for row in rows if row["status"] == name) for name in order}
    local_updates = sum(1 for row in rows if row.get("local", {}).get("update_available"))
    local_errors = sum(1 for row in rows if row.get("local", {}).get("status") == "error")
    local_attention = sum(
        1 for row in rows if row.get("local", {}).get("status") in {"diverged", "error"}
    )
    summary = {
        **counts,
        "upstream_errors": counts["error"],
        "local_errors": local_errors,
        "error": counts["error"] + local_errors,
        "upstream_changes": counts["update_available"],
        "baseline_pending": counts["unbaselined"],
        "local_updates": local_updates,
        "local_attention": local_attention,
    }
    return {"schema_version": 2, "generated_at": generated_at, "summary": summary, "items": rows}


def acknowledge(state: dict, repos: list[str] | None = None) -> int:
    targets = {repo.casefold() for repo in repos} if repos else None
    changed = 0
    for repo, item in state["items"].items():
        if targets is not None and repo.casefold() not in targets:
            continue
        if item.get("error"):
            continue
        observed = item.get("observed")
        if observed is not None and item.get("acknowledged") != observed:
            item["acknowledged"] = observed
            changed += 1
    return changed
