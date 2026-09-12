from __future__ import annotations

import json
from pathlib import Path


LABELS = {
    "update_available": "CHANGED",
    "unbaselined": "BASELINE PENDING",
    "error": "ERROR",
    "up_to_date": "OK",
    "disabled": "DISABLED",
}


def write_reports(report: dict, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "latest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (directory / "latest.md").write_text(render_markdown(report), encoding="utf-8")


def render_markdown(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "# Fossight",
        "",
        f"Generated: {report['generated_at']}",
        "",
        (
            f"LOCAL UPDATES {summary.get('local_updates', 0)} / "
            f"UPSTREAM CHANGES {summary.get('upstream_changes', summary.get('update_available', 0))} / "
            f"ERROR {summary['error']} / DISABLED {summary.get('disabled', 0)}"
        ),
        "",
        "| Local | Upstream change | Repository | Baseline | Current upstream | Priority | Used by |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in report["items"]:
        current = item.get("current", {})
        acknowledged = item.get("acknowledged") or {}
        current_value = current.get("display") or current.get("value") or "-"
        acknowledged_value = acknowledged.get("display") or acknowledged.get("value") or "-"
        local = item.get("local") or {}
        local_label = local.get("status", "unavailable").upper()
        projects = ", ".join(
            f"{usage['project']} ({usage['relation']})".replace("|", "/") for usage in item["usages"]
        )
        lines.append(
            f"| {local_label} | {LABELS[item['status']]} | {item['repo']} | {acknowledged_value} | "
            f"{current_value} | {item['priority']} | {projects} |"
        )
        if item.get("error"):
            lines.append(f"|  |  |  |  | Error: {item['error'].replace('|', '/')} |  |  |")
    return "\n".join(lines) + "\n"
