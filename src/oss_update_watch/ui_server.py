from __future__ import annotations

import json
import re
import threading
import uuid
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import __version__
from .checker import acknowledge, check_registry, load_state, save_state, update_status
from .github import GitHubClient
from .metadata import MetadataCache, describe_repository
from .paths import DataPaths, load_config, save_config
from .prereqs import prerequisites
from .registry import Registry
from .report import write_reports
from .scanner import (
    ScanCancelled,
    ScanResult,
    deep_scan,
    inspect_repository,
    quick_scan,
)


UI_DIR = Path(__file__).with_name("ui")
SUMMARY_FILE = Path("docs") / "oss-summary-catalog.md"

MAX_BODY_BYTES = 65536
MAX_APPLY_SELECTIONS = 500
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self'; "
    "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; "
    "base-uri 'self'; form-action 'self'"
)

_picker_lock = threading.Lock()


def _catalog_roots(registry_dir: Path) -> list[Path]:
    """Locations searched for the curated summary catalog.

    Covers the developer checkout, the packaged bundle (PyInstaller
    ``sys._MEIPASS``), and a data-dir override for user customization.
    """
    roots = [registry_dir]
    try:
        import sys

        bundle = getattr(sys, "_MEIPASS", None)
        if bundle:
            roots.append(Path(bundle))
    except Exception:  # pragma: no cover - defensive
        pass
    repo_root = Path(__file__).resolve().parents[2]
    roots.append(repo_root)
    return roots


def load_summary_catalog(root: Path) -> dict[str, str]:
    path = root / SUMMARY_FILE
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}

    summaries: dict[str, str] = {}
    current_repo: str | None = None
    heading = re.compile(r"^##\s+\d+\.\s+(.+?)\s*$")
    summary = re.compile(r"^-\s+\*\*概要:\*\*\s*(.+?)\s*$")
    for line in text.splitlines():
        heading_match = heading.match(line)
        if heading_match:
            current_repo = heading_match.group(1).strip()
            continue
        summary_match = summary.match(line)
        if current_repo and summary_match:
            summaries[current_repo] = summary_match.group(1).strip()
            current_repo = None
    return summaries


def load_curated_summaries(registry_dir: Path) -> dict[str, str]:
    merged: dict[str, str] = {}
    for root in _catalog_roots(registry_dir):
        # Earlier roots are more specific (for example an explicit/test data
        # directory) and must win over the developer/package fallback catalog.
        for repo, summary in load_summary_catalog(root).items():
            merged.setdefault(repo, summary)
    return merged


def pick_folder_dialog() -> str | None:
    """Open a native folder picker. Returns None when unavailable/cancelled."""
    with _picker_lock:
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            try:
                root.withdraw()
                root.attributes("-topmost", True)
                root.focus_force()
                chosen = filedialog.askdirectory(parent=root, title="Choose a repository folder")
            finally:
                root.destroy()
            return chosen or None
        except Exception:
            return None


def dashboard_payload(
    registry: Registry,
    state: dict,
    summaries: dict[str, str] | None = None,
    cached_summaries: dict[str, str] | None = None,
) -> dict:
    summaries = summaries or {}
    cached_summaries = cached_summaries or {}
    items = []
    latest_check = None
    for item in registry.data["items"]:
        enabled = item.get("enabled", True)
        state_item = state["items"].get(item["repo"], {})
        status = "disabled"
        current = state_item.get("observed")
        acknowledged = state_item.get("acknowledged")
        local = state_item.get("local") or {"status": "unavailable", "update_available": False, "usages": []}
        if not enabled:
            local = {"status": "unavailable", "update_available": False, "usages": []}
        if enabled:
            if state_item.get("error"):
                status = "error"
            elif current:
                status = update_status(current, acknowledged)
            else:
                status = "unbaselined"
        checked_at = state_item.get("checked_at")
        if checked_at and (latest_check is None or checked_at > latest_check):
            latest_check = checked_at
        summary = summaries.get(item["repo"], "") or cached_summaries.get(item["repo"], "")
        items.append(
            {
                **item,
                "enabled": enabled,
                "status": status,
                "current": current,
                "acknowledged": acknowledged,
                "local": local,
                "error": state_item.get("error"),
                "checked_at": checked_at,
                "summary": summary,
            }
        )

    def count(status: str) -> int:
        return sum(1 for item in items if item["status"] == status)

    upstream_changes = count("update_available")
    baseline_pending = count("unbaselined")
    local_updates = sum(1 for item in items if item.get("local", {}).get("update_available"))
    upstream_errors = count("error")
    local_errors = sum(1 for item in items if item.get("local", {}).get("status") == "error")
    local_attention = sum(
        1 for item in items if item.get("local", {}).get("status") in {"diverged", "error"}
    )
    return {
        "summary": {
            "registered": len(items),
            "enabled": sum(1 for item in items if item["enabled"]),
            "disabled": sum(1 for item in items if not item["enabled"]),
            "update_available": count("update_available"),
            "unbaselined": count("unbaselined"),
            "upstream_changes": upstream_changes,
            "baseline_pending": baseline_pending,
            "local_updates": local_updates,
            "local_attention": local_attention,
            "error": upstream_errors + local_errors,
            "upstream_errors": upstream_errors,
            "local_errors": local_errors,
            "up_to_date": count("up_to_date"),
            "usages": sum(len(item["usages"]) for item in items),
        },
        "latest_check": latest_check,
        "items": items,
    }


class ScanJob:
    """One cancellable scan executed on a worker thread."""

    def __init__(self, job_id: str, config: dict, registered: list[str]):
        self.id = job_id
        self.cancel_event = threading.Event()
        self.done = threading.Event()
        self.result: ScanResult | None = None
        self.error: str | None = None
        self.config = config
        self.registered = registered

    def should_cancel(self) -> bool:
        return self.cancel_event.is_set()

    def run(self, roots: list[dict]) -> None:
        try:
            merged = ScanResult()
            for root in roots:
                if self.should_cancel():
                    raise ScanCancelled("cancelled")
                mode = root.get("mode", "quick")
                target = Path(root["path"])
                if mode == "deep":
                    part = deep_scan(
                        target,
                        max_depth=int(self.config["scanner"]["deep_max_depth"]),
                        exclude_names=self.config["scanner"]["exclude_names"],
                        registered_repos=self.registered,
                        should_cancel=self.should_cancel,
                    )
                else:
                    part = quick_scan(target, registered_repos=self.registered, should_cancel=self.should_cancel)
                merged.rows.extend(part.rows)
                merged.errors.extend(part.errors)
                merged.directories_seen += part.directories_seen
                merged.repositories_found += part.repositories_found
                if part.cancelled:
                    merged.cancelled = True
            merged.rows.sort(key=lambda row: (row["status"] != "ok", row["project"].casefold()))
            for row in merged.rows:
                row["selected"] = bool(row["status"] == "ok" and not row["already_registered"])
            self.result = merged
        except Exception as exc:  # surfaced through /api/scan/status
            self.error = str(exc)
        finally:
            self.done.set()


class ScanJobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, ScanJob] = {}
        self._lock = threading.Lock()

    def start(self, roots: list[dict], config: dict, registered: list[str]) -> str:
        job = ScanJob(uuid.uuid4().hex, config, registered)
        with self._lock:
            # Keep only the most recent few jobs to bound memory.
            while len(self._jobs) >= 5:
                oldest = next(iter(self._jobs))
                del self._jobs[oldest]
            self._jobs[job.id] = job
        thread = threading.Thread(target=job.run, args=(roots,), daemon=True)
        thread.start()
        return job.id

    def get(self, job_id: str) -> ScanJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def status(self, job_id: str) -> dict | None:
        job = self.get(job_id)
        if job is None:
            return None
        running = not job.done.is_set()
        result = job.result
        payload: dict = {
            "job": job.id,
            "running": running,
            "cancelled": bool(result and result.cancelled),
            "error": job.error,
            "progress": {
                "directories_seen": result.directories_seen if result else 0,
                "repositories_found": result.repositories_found if result else 0,
            },
            "rows": None,
            "counts": None,
        }
        if not running and result is not None:
            payload["rows"] = result.rows
            payload["counts"] = result.counts()
        return payload

    def cancel(self, job_id: str) -> bool:
        job = self.get(job_id)
        if job is None:
            return False
        job.cancel_event.set()
        return True


class _AppServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address,
        handler,
        registry_path: Path,
        state_path: Path,
        reports_path: Path,
        config_path: Path | None = None,
        metadata_cache_path: Path | None = None,
    ):
        super().__init__(address, handler)
        self.registry_path = registry_path
        self.state_path = state_path
        self.reports_path = reports_path
        self.config_path = config_path or (registry_path.parent / "config.json")
        self.metadata_cache = MetadataCache(
            metadata_cache_path or (registry_path.parent / "cache" / "repository-metadata.json")
        )
        self.scans = ScanJobManager()
        self.metadata_client_factory = GitHubClient

    # Convenience accessors -------------------------------------------------
    @property
    def data_paths(self) -> DataPaths:
        return DataPaths(root=self.registry_path.parent)

    def registered_repos(self) -> list[str]:
        return [item["repo"] for item in Registry.load(self.registry_path).data["items"]]

    def dashboard(self, registry: Registry, state: dict) -> dict:
        summaries = load_curated_summaries(self.registry_path.parent)
        cached: dict[str, str] = {}
        for item in registry.data["items"]:
            if item["repo"] in summaries:
                continue
            entry = self.metadata_cache.get(item["repo"])
            if entry and entry.get("summary"):
                cached[item["repo"]] = entry["summary"]
        return dashboard_payload(registry, state, summaries, cached)

    def apply_config(self, config: dict) -> None:
        save_config(self.config_path, config)


class _Handler(BaseHTTPRequestHandler):
    server: _AppServer

    def log_message(self, format: str, *args) -> None:
        return

    def _security_headers(self) -> None:
        self.send_header("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")

    def _json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _error(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self._json({"error": message}, status)

    def _read_json(self) -> dict:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise ValueError("Content-Type must be application/json")
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_BODY_BYTES:
            raise ValueError("Invalid request body size")
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
        return payload

    def _serve_asset(self, name: str, content_type: str) -> None:
        path = UI_DIR / name
        try:
            body = path.read_bytes()
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    # ------------------------------------------------------------------ GET
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path in {"/", "/index.html"}:
            self._serve_asset("index.html", "text/html; charset=utf-8")
            return
        if path == "/styles.css":
            self._serve_asset("styles.css", "text/css; charset=utf-8")
            return
        if path == "/app.js":
            self._serve_asset("app.js", "text/javascript; charset=utf-8")
            return
        if path == "/api/registry":
            registry = Registry.load(self.server.registry_path)
            state = load_state(self.server.state_path)
            self._json(self.server.dashboard(registry, state))
            return
        if path == "/api/settings":
            self._json({"config": load_config(self.server.config_path)})
            return
        if path == "/api/prerequisites":
            self._json(prerequisites())
            return
        if path == "/api/scan/status":
            job_id = (parse_qs(parsed.query).get("job") or [""])[0]
            status = self.server.scans.status(job_id)
            if status is None:
                self._error("Unknown scan job", HTTPStatus.NOT_FOUND)
                return
            self._json(status)
            return
        if path == "/api/repository-metadata":
            repo = (parse_qs(parsed.query).get("repo") or [""])[0]
            try:
                from .registry import normalize_repo

                repo = normalize_repo(repo)
            except ValueError:
                self._error("repo must be owner/repo")
                return
            curated = load_curated_summaries(self.server.registry_path.parent).get(repo)
            if curated:
                self._json({"repo": repo, "summary": curated, "source": "curated", "cached": False, "fetched_at": None})
                return
            client = self.server.metadata_client_factory()
            payload = describe_repository(repo, client, self.server.metadata_cache)
            payload["repo"] = repo
            self._json(payload)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    # ----------------------------------------------------------------- POST
    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/enabled":
                payload = self._read_json()
                repo = payload.get("repo")
                enabled = payload.get("enabled")
                if not isinstance(repo, str) or not isinstance(enabled, bool):
                    raise ValueError("repo must be a string and enabled must be a boolean")
                registry = Registry.load(self.server.registry_path)
                registry.set_enabled(repo, enabled)
                registry.save(self.server.registry_path)
                self._json({"repo": repo, "enabled": enabled})
                return
            if path == "/api/check":
                self._read_json()
                registry = Registry.load(self.server.registry_path)
                state = load_state(self.server.state_path)
                report = check_registry(registry.data, state, registry_dir=self.server.registry_path.parent)
                save_state(self.server.state_path, state)
                write_reports(report, self.server.reports_path)
                self._json(self.server.dashboard(registry, state))
                return
            if path == "/api/ack":
                self._read_json()
                state = load_state(self.server.state_path)
                changed = acknowledge(state)
                save_state(self.server.state_path, state)
                registry = Registry.load(self.server.registry_path)
                self._json({"changed": changed, "dashboard": self.server.dashboard(registry, state)})
                return
            if path == "/api/settings":
                payload = self._read_json()
                config = payload.get("config")
                if not isinstance(config, dict):
                    raise ValueError("config must be an object")
                save_config(self.server.config_path, config)
                self._json({"config": load_config(self.server.config_path)})
                return
            if path == "/api/scan/start":
                payload = self._read_json()
                roots = payload.get("roots")
                if not isinstance(roots, list) or not roots or len(roots) > 32:
                    raise ValueError("roots must be a non-empty list (max 32)")
                normalized = []
                for root in roots:
                    if not isinstance(root, dict):
                        raise ValueError("each root must be an object")
                    value = root.get("path")
                    mode = root.get("mode", "quick")
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError("each root needs a non-empty path")
                    if mode not in {"quick", "deep"}:
                        raise ValueError("root mode must be quick or deep")
                    normalized.append({"path": value, "mode": mode})
                config = load_config(self.server.config_path)
                job_id = self.server.scans.start(normalized, config, self.server.registered_repos())
                self._json({"job": job_id})
                return
            if path == "/api/scan/cancel":
                payload = self._read_json()
                job_id = payload.get("job")
                if not isinstance(job_id, str):
                    raise ValueError("job must be a string")
                if not self.server.scans.cancel(job_id):
                    self._error("Unknown scan job", HTTPStatus.NOT_FOUND)
                    return
                self._json({"job": job_id, "cancelling": True})
                return
            if path == "/api/scan/apply":
                payload = self._read_json()
                self._apply_scan(payload)
                return
            if path == "/api/pick-folder":
                self._read_json()
                chosen = pick_folder_dialog()
                self._json({"path": chosen, "available": chosen is not None})
                return
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self._error(str(exc))
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def _apply_scan(self, payload: dict) -> None:
        job_id = payload.get("job")
        selections = payload.get("local_paths")
        if not isinstance(job_id, str):
            raise ValueError("job must be a string")
        if not isinstance(selections, list) or not selections or len(selections) > MAX_APPLY_SELECTIONS:
            raise ValueError(f"local_paths must be a non-empty list (max {MAX_APPLY_SELECTIONS})")
        if not all(isinstance(item, str) for item in selections):
            raise ValueError("local_paths must contain strings")
        job = self.server.scans.get(job_id)
        if job is None or job.result is None:
            raise ValueError("Scan preview is no longer available; scan again")

        registry = Registry.load(self.server.registry_path)
        wanted = {value for value in selections}
        applied: list[dict] = []
        registered = {item["repo"].casefold() for item in registry.data["items"]}
        for row in job.result.rows:
            if row["local_path"] not in wanted or row["status"] != "ok":
                continue
            # Re-derive repo/relation from the repository itself so a stale or
            # tampered preview can never write an arbitrary repo into the
            # registry. Preview rows are a selection UI, not the source of truth.
            fresh = inspect_repository(Path(row["local_path"]), registered)
            if fresh["status"] != "ok":
                continue
            changed = registry.add_usage(
                fresh["repo"],
                fresh["project"],
                fresh["relation"],
                fresh["local_path"],
            )
            applied.append({**fresh, "changed": changed})
        if applied:
            config = load_config(self.server.config_path)
            config["onboarding_complete"] = True
            self.server.apply_config(config)
        registry.save(self.server.registry_path)
        state = load_state(self.server.state_path)
        self._json({"applied": applied, "dashboard": self.server.dashboard(registry, state)})


def create_server(
    registry_path: Path,
    state_path: Path,
    reports_path: Path,
    port: int = 18765,
    *,
    config_path: Path | None = None,
    metadata_cache_path: Path | None = None,
) -> _AppServer:
    if not 0 <= port <= 65535:
        raise ValueError("port must be between 0 and 65535")
    return _AppServer(
        ("127.0.0.1", port),
        _Handler,
        registry_path.resolve(),
        state_path.resolve(),
        reports_path.resolve(),
        config_path=config_path,
        metadata_cache_path=metadata_cache_path,
    )


def create_data_server(data_paths: DataPaths, port: int = 18765) -> _AppServer:
    """Create the UI server from a resolved user data directory."""
    return create_server(
        data_paths.registry,
        data_paths.state,
        data_paths.reports,
        port,
        config_path=data_paths.config,
        metadata_cache_path=data_paths.metadata_cache,
    )


def serve_ui(
    registry_path: Path,
    state_path: Path,
    reports_path: Path,
    port: int = 18765,
    *,
    open_browser: bool = True,
    config_path: Path | None = None,
    metadata_cache_path: Path | None = None,
) -> None:
    server = create_server(
        registry_path,
        state_path,
        reports_path,
        port,
        config_path=config_path,
        metadata_cache_path=metadata_cache_path,
    )
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Fossight UI: {url}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
