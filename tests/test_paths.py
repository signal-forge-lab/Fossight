import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oss_update_watch.cli import main
from oss_update_watch.paths import (
    CONFIG_SCHEMA_VERSION,
    DataPaths,
    default_config,
    default_data_dir,
    ensure_data_dir,
    load_config,
    migrate_legacy_data,
    migrate_previous_appdata,
    resolve_data_dir,
    save_config,
)


class DataDirResolutionTests(unittest.TestCase):
    def test_default_data_dir_prefers_localappdata(self):
        with patch.dict("os.environ", {"LOCALAPPDATA": r"C:\Users\t\AppData\Local"}):
            self.assertEqual(default_data_dir(), Path(r"C:\Users\t\AppData\Local\FossightData"))

    def test_default_data_dir_falls_back_to_xdg_then_home(self):
        with patch.dict("os.environ", {"LOCALAPPDATA": "", "XDG_DATA_HOME": "/xdg"}):
            self.assertEqual(default_data_dir(), Path("/xdg/Fossight"))
        env = {
            "LOCALAPPDATA": "",
            "XDG_DATA_HOME": "",
            "USERPROFILE": "/home/t",
            "HOMEDRIVE": "",
            "HOMEPATH": "",
        }
        with patch.dict("os.environ", env):
            self.assertEqual(default_data_dir(), Path("/home/t/.local/share/Fossight"))

    def test_resolution_precedence_explicit_over_env_over_default(self):
        with patch.dict("os.environ", {"FOSSIGHT_DATA_DIR": "/env/dir"}):
            self.assertEqual(resolve_data_dir(), Path("/env/dir"))
            self.assertEqual(resolve_data_dir("/explicit/dir"), Path("/explicit/dir"))
        with patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("FOSSIGHT_DATA_DIR", None)
            self.assertEqual(resolve_data_dir(), default_data_dir())


class ConfigTests(unittest.TestCase):
    def test_missing_config_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = load_config(Path(tmp) / "config.json")
        self.assertEqual(config["schema_version"], CONFIG_SCHEMA_VERSION)
        self.assertEqual(config["scan_roots"], [])
        self.assertEqual(config["scanner"]["deep_max_depth"], 4)
        self.assertFalse(config["onboarding_complete"])

    def test_config_round_trip_and_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            config = default_config()
            config["scan_roots"] = [{"path": "D:\\GitHub", "mode": "quick", "enabled": True}]
            save_config(path, config)
            self.assertEqual(load_config(path), config)

            bad = default_config()
            bad["scanner"]["deep_max_depth"] = 99
            with self.assertRaises(ValueError):
                save_config(path, bad)

            bad = default_config()
            bad["schema_version"] = 2
            with self.assertRaises(ValueError):
                save_config(path, bad)

    def test_load_config_repairs_invalid_documents(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text("{not json", encoding="utf-8")
            self.assertEqual(load_config(path)["schema_version"], CONFIG_SCHEMA_VERSION)
            path.write_text(json.dumps({"schema_version": 1, "scanner": {"deep_max_depth": 0}}), encoding="utf-8")
            self.assertEqual(load_config(path)["scanner"]["deep_max_depth"], 4)


class MigrationTests(unittest.TestCase):
    def _legacy_root(self, root: Path) -> Path:
        legacy = root / "legacy-repo"
        (legacy / ".state").mkdir(parents=True)
        (legacy / "reports").mkdir()
        (legacy / "oss-registry.json").write_text(json.dumps({"schema_version": 1, "items": []}), encoding="utf-8")
        (legacy / ".state" / "state.json").write_text(json.dumps({"schema_version": 1, "items": {}}), encoding="utf-8")
        (legacy / "reports" / "latest.md").write_text("# report\n", encoding="utf-8")
        return legacy

    def test_migration_copies_legacy_data_into_empty_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = self._legacy_root(root)
            paths = DataPaths(root=root / "data")
            ensure_data_dir(paths)

            report = migrate_legacy_data(paths, legacy)

            self.assertTrue(report["migrated"])
            self.assertEqual(sorted(report["copied"]), ["latest.md", "registry.json", "state.json"])
            self.assertTrue(paths.registry.is_file())
            self.assertTrue(paths.state.is_file())
            self.assertTrue((paths.reports / "latest.md").is_file())
            # Legacy data stays in place: the developer checkout keeps working.
            self.assertTrue((legacy / "oss-registry.json").is_file())

    def test_migration_never_overwrites_nonempty_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = self._legacy_root(root)
            paths = DataPaths(root=root / "data")
            ensure_data_dir(paths)
            paths.registry.write_text(json.dumps({"schema_version": 1, "items": []}), encoding="utf-8")

            report = migrate_legacy_data(paths, legacy)

            self.assertFalse(report["migrated"])
            self.assertEqual(report["skipped_reason"], "target_registry_exists")

    def test_migration_without_legacy_data_is_a_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = DataPaths(root=root / "data")
            ensure_data_dir(paths)
            report = migrate_legacy_data(paths, root / "missing")
            self.assertFalse(report["migrated"])
            self.assertEqual(report["skipped_reason"], "no_legacy_data")

    def test_previous_appdata_migration_copies_only_known_user_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            previous = root / "Fossight"
            previous.mkdir()
            (previous / "config.json").write_text(json.dumps(default_config()), encoding="utf-8")
            (previous / "registry.json").write_text(json.dumps({"schema_version": 1, "items": []}), encoding="utf-8")
            (previous / "oss-update-watch-desktop.exe").write_bytes(b"do-not-copy")
            (previous / "uninstall.exe").write_bytes(b"do-not-copy")
            (previous / "cache").mkdir()
            (previous / "cache" / "repository-metadata.json").write_text("{}", encoding="utf-8")
            paths = DataPaths(root=root / "FossightData")
            ensure_data_dir(paths)

            report = migrate_previous_appdata(paths, previous)

            self.assertTrue(report["migrated"])
            self.assertTrue(paths.registry.is_file())
            self.assertTrue(paths.config.is_file())
            self.assertTrue(paths.metadata_cache.is_file())
            self.assertFalse((paths.root / "oss-update-watch-desktop.exe").exists())
            self.assertFalse((paths.root / "uninstall.exe").exists())


class CliDataDirTests(unittest.TestCase):
    def test_cli_defaults_to_data_dir_and_migrates_legacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            legacy = root / "legacy"
            legacy.mkdir()
            (legacy / "oss-registry.json").write_text(
                json.dumps({"schema_version": 1, "items": []}), encoding="utf-8"
            )

            with patch("oss_update_watch.cli.legacy_repo_root", return_value=legacy):
                self.assertEqual(main(["--data-dir", str(data), "list"]), 0)

            self.assertTrue((data / "registry.json").is_file())
            self.assertTrue((data / "config.json").is_file())

    def test_cli_explicit_overrides_avoid_the_data_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path = root / "registry.json"
            with tempfile.TemporaryDirectory() as sandbox:
                with patch("oss_update_watch.cli.ensure_data_dir") as ensure:
                    exit_code = main(
                        [
                            "--registry",
                            str(registry_path),
                            "--state",
                            str(root / "state.json"),
                            "--reports",
                            str(root / "reports"),
                            "--data-dir",
                            str(sandbox),
                            "add",
                            "owner/repo",
                            "--project",
                            "tool",
                        ]
                    )
                    ensure.assert_not_called()
            self.assertEqual(exit_code, 0)
            self.assertTrue(registry_path.is_file())


if __name__ == "__main__":
    unittest.main()
