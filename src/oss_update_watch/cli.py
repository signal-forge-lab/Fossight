from __future__ import annotations

import argparse
import os
import json
import os
from pathlib import Path

from .checker import acknowledge, check_registry, load_state, save_state
from .discovery import discover_repositories
from .paths import (
    DATA_DIR_ENV,
    DataPaths,
    ensure_data_dir,
    legacy_repo_root,
    migrate_legacy_data,
    migrate_previous_appdata,
    previous_windows_data_dir,
    resolve_data_dir,
)
from .registry import PRIORITIES, RELATIONS, TRACK_MODES, Registry, normalize_repo
from .report import write_reports
from .ui_server import serve_ui


ROOT = Path(__file__).resolve().parents[2]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="oss-watch", description="Track upstream updates for actively used GitHub OSS.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="User data directory (default: %%LOCALAPPDATA%%\\FossightData, override with FOSSIGHT_DATA_DIR)",
    )
    parser.add_argument("--registry", type=Path, default=None, help="Override the registry file path")
    parser.add_argument("--state", type=Path, default=None, help="Override the state file path")
    parser.add_argument("--reports", type=Path, default=None, help="Override the reports directory path")
    commands = parser.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add", help="Add an OSS usage to the registry")
    add.add_argument("repo", help="owner/repo or a github.com repository URL")
    add.add_argument("--project", required=True, help="Local project/tool that uses this OSS")
    add.add_argument("--relation", choices=sorted(RELATIONS), default="direct")
    add.add_argument("--path", dest="local_path", help="Optional local checkout path")
    add.add_argument("--track", choices=sorted(TRACK_MODES))
    add.add_argument("--branch", help="Required when --track branch is selected")
    add.add_argument("--priority", choices=sorted(PRIORITIES))

    remove = commands.add_parser("remove", help="Remove one usage or the complete OSS entry")
    remove.add_argument("repo")
    remove_group = remove.add_mutually_exclusive_group(required=True)
    remove_group.add_argument("--project", help="Remove this project's usage")
    remove_group.add_argument("--all", action="store_true", help="Remove the OSS entry and all usages")

    list_cmd = commands.add_parser("list", help="Show the current registry")
    list_cmd.add_argument("--json", action="store_true", help="Print the registry JSON")

    discover = commands.add_parser("discover", help="Find GitHub clones/forks under a local directory")
    discover.add_argument("path", nargs="?", type=Path, default=ROOT.parent / "github")
    discover.add_argument("--apply", action="store_true", help="Add discovered repositories to the registry")
    discover.add_argument("--track", choices=sorted(TRACK_MODES), default="auto")
    discover.add_argument("--branch")
    discover.add_argument("--priority", choices=sorted(PRIORITIES), default="normal")

    commands.add_parser("check", help="Check all registered upstream repositories and write reports")

    enabled = commands.add_parser("enable", help="Enable update checks for one OSS")
    enabled.add_argument("repo")
    disabled = commands.add_parser("disable", help="Disable update checks for one OSS")
    disabled.add_argument("repo")

    ui = commands.add_parser("ui", help="Start the local management UI")
    ui.add_argument("--port", type=int, default=18765)
    ui.add_argument("--no-open", action="store_true", help="Do not open the browser automatically")

    ack = commands.add_parser("ack", help="Mark observed upstream versions as reviewed")
    ack.add_argument("repos", nargs="*")
    ack.add_argument("--all", action="store_true")
    return parser


def _relative_local_path(value: str | None, base: Path) -> str | None:
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        return value
    try:
        return os.path.relpath(path, base)
    except ValueError:
        return str(path)


def _remove_state_repo(state: dict, repo: str) -> bool:
    needle = normalize_repo(repo).casefold()
    key = next((key for key in state["items"] if key.casefold() == needle), None)
    if key is None:
        return False
    del state["items"][key]
    return True


def _print_registry(registry: Registry) -> None:
    if not registry.data["items"]:
        print("Registry is empty.")
        return
    for item in registry.data["items"]:
        tracking = item["tracking"]["mode"]
        if tracking == "branch":
            tracking += f":{item['tracking']['branch']}"
        uses = ", ".join(f"{usage['project']}:{usage['relation']}" for usage in item["usages"])
        print(f"{item['repo']:<42} {tracking:<20} {item['priority']:<7} {uses}")


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    data_paths = DataPaths(root=resolve_data_dir(args.data_dir))
    explicit_paths = any((args.registry, args.state, args.reports))
    registry_path = (args.registry or data_paths.registry).resolve()
    state_path = (args.state or data_paths.state).resolve()
    reports_path = (args.reports or data_paths.reports).resolve()
    if not explicit_paths:
        # Default layout: create the user data directory and import legacy
        # developer-checkout data into an empty profile. Explicit overrides
        # (tests/developer mode) never touch the user data directory.
        ensure_data_dir(data_paths)
        if not registry_path.exists():
            if args.data_dir is None and not os.environ.get(DATA_DIR_ENV):
                previous = previous_windows_data_dir()
                if previous is not None:
                    migrate_previous_appdata(data_paths, previous)
        if not registry_path.exists():
            legacy_root = legacy_repo_root()
            if legacy_root is not None:
                migrate_legacy_data(data_paths, legacy_root)
    registry = Registry.load(registry_path)

    try:
        if args.command == "add":
            if args.branch and args.track != "branch":
                parser.error("--branch requires --track branch")
            changed = registry.add_usage(
                args.repo,
                args.project,
                args.relation,
                _relative_local_path(args.local_path, registry_path.parent),
                track=args.track,
                branch=args.branch,
                priority=args.priority,
            )
            registry.save(registry_path)
            print(("Added/updated " if changed else "Already registered ") + normalize_repo(args.repo))
            return 0

        if args.command == "remove":
            changed = registry.remove_usage(args.repo, args.project, remove_all=args.all)
            if not changed:
                print("No matching registry entry.")
                return 1
            registry.save(registry_path)
            if registry.find(args.repo) is None:
                state = load_state(state_path)
                if _remove_state_repo(state, args.repo):
                    save_state(state_path, state)
            print(f"Removed {normalize_repo(args.repo)}")
            return 0

        if args.command == "list":
            if args.json:
                print(json.dumps(registry.data, ensure_ascii=False, indent=2))
            else:
                _print_registry(registry)
            return 0

        if args.command == "discover":
            if args.branch and args.track != "branch":
                parser.error("discover --branch requires --track branch")
            if args.track == "branch" and not args.branch:
                parser.error("discover --track branch requires --branch")
            found = discover_repositories(args.path)
            if not found:
                print("No GitHub repositories discovered.")
                return 0
            added = 0
            for candidate in found:
                print(f"{candidate['repo']:<42} {candidate['relation']:<9} {candidate['project']}")
                if args.apply:
                    existing = registry.find(candidate["repo"])
                    changed = registry.add_usage(
                        candidate["repo"],
                        candidate["project"],
                        candidate["relation"],
                        _relative_local_path(candidate["local_path"], registry_path.parent),
                        track=None if existing else args.track,
                        branch=None if existing else args.branch,
                        priority=None if existing else args.priority,
                    )
                    added += int(changed)
            if args.apply:
                registry.save(registry_path)
                print(f"Applied {added} registry change(s).")
            return 0

        if args.command == "check":
            state = load_state(state_path)
            report = check_registry(registry.data, state, registry_dir=registry_path.parent)
            save_state(state_path, state)
            write_reports(report, reports_path)
            summary = report["summary"]
            print(
                f"LOCAL_UPDATES={summary['local_updates']} UPSTREAM_CHANGES={summary['upstream_changes']} "
                f"ERROR={summary['error']} LOCAL_ATTENTION={summary['local_attention']}"
            )
            print(reports_path / "latest.md")
            return 2 if summary["error"] else (
                1 if summary["local_updates"] or summary["upstream_changes"] or summary["local_attention"] else 0
            )

        if args.command in {"enable", "disable"}:
            enabled_value = args.command == "enable"
            registry.set_enabled(args.repo, enabled_value)
            registry.save(registry_path)
            print(f"{normalize_repo(args.repo)}: {'enabled' if enabled_value else 'disabled'}")
            return 0

        if args.command == "ui":
            serve_ui(
                registry_path,
                state_path,
                reports_path,
                args.port,
                open_browser=not args.no_open,
                config_path=data_paths.config if not explicit_paths else None,
                metadata_cache_path=data_paths.metadata_cache if not explicit_paths else None,
            )
            return 0

        if args.command == "ack":
            if args.all and args.repos:
                parser.error("ack accepts repository names or --all, not both")
            if not args.all and not args.repos:
                parser.error("ack requires at least one repository or --all")
            state = load_state(state_path)
            repos = None if args.all else [normalize_repo(repo) for repo in args.repos]
            changed = acknowledge(state, repos)
            save_state(state_path, state)
            print(f"Acknowledged {changed} upstream value(s).")
            return 0
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
