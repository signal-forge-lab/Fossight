"""Central Fossight user-data directory resolution.

All mutable user data (config, registry, state, reports, cache, logs) lives
in one per-user data directory. On Windows the recommended location is
``%LOCALAPPDATA%\\FossightData`` so it never collides with the default
current-user NSIS install directory (``%LOCALAPPDATA%\\Fossight``).
Explicit overrides (CLI flag or environment
variable) keep developer and test workflows isolated.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path


APP_DIR_NAME = "Fossight"
WINDOWS_DATA_DIR_NAME = "FossightData"
DATA_DIR_ENV = "FOSSIGHT_DATA_DIR"

CONFIG_NAME = "config.json"
REGISTRY_NAME = "registry.json"
STATE_NAME = "state.json"
REPORTS_DIR_NAME = "reports"
CACHE_DIR_NAME = "cache"
LOGS_DIR_NAME = "logs"
METADATA_CACHE_NAME = "repository-metadata.json"

# Legacy developer-checkout locations (relative to the repository root).
LEGACY_REGISTRY_NAME = "oss-registry.json"
LEGACY_STATE_RELATIVE = Path(".state") / "state.json"
LEGACY_REPORTS_DIR_NAME = "reports"

CONFIG_SCHEMA_VERSION = 1

DEFAULT_EXCLUDE_NAMES = [
    ".workbridge", "node_modules", ".venv", "venv",
    "target", "dist", "build", "vendor",
]


def default_data_dir() -> Path:
    """Return the platform-appropriate default data directory."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / WINDOWS_DATA_DIR_NAME
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / APP_DIR_NAME
    return Path.home() / ".local" / "share" / APP_DIR_NAME


def previous_windows_data_dir() -> Path | None:
    """Return the pre-0.9.1 Windows data location, if applicable."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return None
    return Path(local_app_data) / APP_DIR_NAME


def resolve_data_dir(explicit: Path | str | None = None) -> Path:
    """Resolve the data directory from explicit value, env, or default."""
    if explicit:
        return Path(explicit).expanduser()
    env_value = os.environ.get(DATA_DIR_ENV)
    if env_value:
        return Path(env_value).expanduser()
    return default_data_dir()


@dataclass(frozen=True)
class DataPaths:
    """Resolved locations of every mutable Fossight data file."""

    root: Path

    @property
    def config(self) -> Path:
        return self.root / CONFIG_NAME

    @property
    def registry(self) -> Path:
        return self.root / REGISTRY_NAME

    @property
    def state(self) -> Path:
        return self.root / STATE_NAME

    @property
    def reports(self) -> Path:
        return self.root / REPORTS_DIR_NAME

    @property
    def cache(self) -> Path:
        return self.root / CACHE_DIR_NAME

    @property
    def logs(self) -> Path:
        return self.root / LOGS_DIR_NAME

    @property
    def metadata_cache(self) -> Path:
        return self.cache / METADATA_CACHE_NAME


def default_config() -> dict:
    return {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "scan_roots": [],
        "scanner": {
            "deep_max_depth": 4,
            "exclude_names": list(DEFAULT_EXCLUDE_NAMES),
        },
        "onboarding_complete": False,
    }


def load_config(path: Path) -> dict:
    """Load config.json, returning defaults when absent or unusable."""
    if not path.exists():
        return default_config()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_config()
    if not isinstance(data, dict):
        return default_config()
    merged = default_config()
    if isinstance(data.get("scan_roots"), list):
        merged["scan_roots"] = data["scan_roots"]
    if isinstance(data.get("scanner"), dict):
        scanner = merged["scanner"]
        depth = data["scanner"].get("deep_max_depth")
        if isinstance(depth, int) and 1 <= depth <= 32:
            scanner["deep_max_depth"] = depth
        excludes = data["scanner"].get("exclude_names")
        if isinstance(excludes, list) and all(isinstance(name, str) for name in excludes):
            scanner["exclude_names"] = excludes
    if isinstance(data.get("onboarding_complete"), bool):
        merged["onboarding_complete"] = data["onboarding_complete"]
    return merged


def save_config(path: Path, config: dict) -> None:
    """Persist config.json after validating the supported schema."""
    if config.get("schema_version") != CONFIG_SCHEMA_VERSION:
        raise ValueError(f"config schema_version must be {CONFIG_SCHEMA_VERSION}")
    if not isinstance(config.get("scan_roots"), list):
        raise ValueError("scan_roots must be a list")
    scanner = config.get("scanner")
    if not isinstance(scanner, dict):
        raise ValueError("scanner must be an object")
    depth = scanner.get("deep_max_depth")
    if not isinstance(depth, int) or not 1 <= depth <= 32:
        raise ValueError("scanner.deep_max_depth must be an integer between 1 and 32")
    excludes = scanner.get("exclude_names")
    if not isinstance(excludes, list) or not all(isinstance(name, str) and name for name in excludes):
        raise ValueError("scanner.exclude_names must be a list of non-empty strings")
    if not isinstance(config.get("onboarding_complete"), bool):
        raise ValueError("onboarding_complete must be a boolean")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_data_dir(paths: DataPaths) -> Path:
    """Create the data directory layout and return the root."""
    for directory in (paths.root, paths.reports, paths.cache, paths.logs):
        directory.mkdir(parents=True, exist_ok=True)
    if not paths.config.exists():
        save_config(paths.config, default_config())
    return paths.root


def legacy_repo_root() -> Path | None:
    """Return the developer-checkout root when running from a source tree."""
    candidate = Path(__file__).resolve().parents[2]
    if (candidate / LEGACY_REGISTRY_NAME).is_file() or (candidate / ".git").is_dir():
        return candidate
    return None


def migrate_legacy_data(paths: DataPaths, legacy_root: Path) -> dict:
    """Import legacy repo-local data into an empty AppData profile.

    Migration only runs when the target registry does not exist yet, so a
    non-empty AppData dataset is never overwritten. Legacy files are copied,
    never moved: the developer's in-repo data keeps working.
    """
    report = {"migrated": False, "copied": [], "skipped_reason": None}
    if paths.registry.exists():
        report["skipped_reason"] = "target_registry_exists"
        return report

    sources = [
        (legacy_root / LEGACY_REGISTRY_NAME, paths.registry),
        (legacy_root / LEGACY_STATE_RELATIVE, paths.state),
    ]
    legacy_reports = legacy_root / LEGACY_REPORTS_DIR_NAME
    if legacy_reports.is_dir():
        for item in sorted(legacy_reports.iterdir()):
            if item.is_file():
                sources.append((item, paths.reports / item.name))

    copied: list[str] = []
    for source, target in sources:
        if not source.is_file():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(target.name)

    if copied:
        report["migrated"] = True
        report["copied"] = copied
    else:
        report["skipped_reason"] = "no_legacy_data"
    return report


def migrate_previous_appdata(paths: DataPaths, previous_root: Path) -> dict:
    """Copy known mutable data from the old Windows AppData directory.

    Fossight 0.7-0.9.0 used ``%LOCALAPPDATA%\\Fossight`` for data, which is
    also Tauri NSIS' default current-user install directory. 0.9.1 separates
    data into ``FossightData``. Only known data files/directories are copied;
    installed executables and uninstallers are deliberately ignored.
    """
    report = {"migrated": False, "copied": [], "skipped_reason": None}
    try:
        if previous_root.resolve() == paths.root.resolve():
            report["skipped_reason"] = "same_directory"
            return report
    except OSError:
        pass
    if paths.registry.exists():
        report["skipped_reason"] = "target_registry_exists"
        return report
    if not previous_root.is_dir():
        report["skipped_reason"] = "previous_directory_missing"
        return report

    file_sources = [
        (previous_root / CONFIG_NAME, paths.config),
        (previous_root / REGISTRY_NAME, paths.registry),
        (previous_root / STATE_NAME, paths.state),
    ]
    copied: list[str] = []
    for source, target in file_sources:
        if not source.is_file():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(target.name)

    for dirname in (REPORTS_DIR_NAME, CACHE_DIR_NAME, LOGS_DIR_NAME):
        source_dir = previous_root / dirname
        target_dir = paths.root / dirname
        if not source_dir.is_dir():
            continue
        shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
        copied.append(dirname + "/")

    if copied:
        report["migrated"] = True
        report["copied"] = copied
    else:
        report["skipped_reason"] = "no_previous_data"
    return report


def resolve_user_paths(explicit_data_dir: Path | str | None = None) -> DataPaths:
    """Resolve, create, and (when empty) migrate the user data directory."""
    paths = DataPaths(root=resolve_data_dir(explicit_data_dir))
    ensure_data_dir(paths)
    if not paths.registry.exists():
        legacy_root = legacy_repo_root()
        if legacy_root is not None:
            migrate_legacy_data(paths, legacy_root)
    return paths
