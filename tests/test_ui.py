import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from oss_update_watch.registry import Registry
from oss_update_watch.ui_server import create_server, load_summary_catalog


class UiServerTests(unittest.TestCase):
    def test_onboarding_overlay_can_be_hidden(self):
        css = (
            Path(__file__).parents[1]
            / "src"
            / "oss_update_watch"
            / "ui"
            / "styles.css"
        ).read_text(encoding="utf-8")
        self.assertIn(".onboarding-overlay[hidden] { display: none; }", css)

    @staticmethod
    def _post_json(url, payload):
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request) as response:
            return json.load(response)

    def test_server_binds_loopback_only_and_rejects_bad_request_bodies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path = root / "registry.json"
            state_path = root / "state.json"
            reports_path = root / "reports"
            Registry.empty().save(registry_path)
            server = create_server(registry_path, state_path, reports_path, port=0)
            self.assertEqual(server.server_address[0], "127.0.0.1")
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_address[1]}"
                cases = [
                    (b"not-json", "application/json"),
                    (b"[]", "application/json"),
                    (b"{}", "text/plain"),
                    (b"{\"x\":\"" + (b"a" * 65536) + b"\"}", "application/json"),
                ]
                for body, content_type in cases:
                    request = Request(
                        base + "/api/settings",
                        data=body,
                        headers={"Content-Type": content_type},
                        method="POST",
                    )
                    with self.assertRaises(HTTPError) as caught:
                        urlopen(request)
                    self.assertEqual(caught.exception.code, 400)
                    caught.exception.close()

                with urlopen(base + "/") as response:
                    self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
                    self.assertEqual(response.headers.get("Referrer-Policy"), "no-referrer")
                    self.assertTrue(response.headers.get("Content-Security-Policy"))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_summary_catalog_is_loaded_by_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir()
            (docs / "oss-summary-catalog.md").write_text(
                "# OSS Summary Catalog\n\n"
                "## 01. microsoft/UFO\n\n"
                "- **Repo:** `microsoft/UFO`\n"
                "- **概要:** Windowsを操作するGUI Agent基盤です。\n",
                encoding="utf-8",
            )
            self.assertEqual(
                load_summary_catalog(root),
                {"microsoft/UFO": "Windowsを操作するGUI Agent基盤です。"},
            )

    def test_registry_api_and_enabled_toggle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path = root / "registry.json"
            state_path = root / "state.json"
            reports_path = root / "reports"
            registry = Registry.empty()
            registry.add_usage("microsoft/UFO", "UFO", "direct", "../github/UFO")
            registry.save(registry_path)
            docs = root / "docs"
            docs.mkdir()
            (docs / "oss-summary-catalog.md").write_text(
                "## 01. microsoft/UFO\n\n- **概要:** Windowsを操作するGUI Agent基盤です。\n",
                encoding="utf-8",
            )

            server = create_server(registry_path, state_path, reports_path, port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_address[1]}"
                with urlopen(base + "/") as response:
                    html = response.read().decode("utf-8")
                self.assertIn("<title>Fossight</title>", html)
                self.assertIn(">Fossight</span>", html)

                with urlopen(base + "/api/registry") as response:
                    payload = json.load(response)
                self.assertEqual(payload["summary"]["enabled"], 1)
                self.assertTrue(payload["items"][0]["enabled"])
                self.assertEqual(payload["items"][0]["summary"], "Windowsを操作するGUI Agent基盤です。")

                body = json.dumps({"repo": "microsoft/UFO", "enabled": False}).encode("utf-8")
                request = Request(
                    base + "/api/enabled",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request) as response:
                    changed = json.load(response)
                self.assertFalse(changed["enabled"])

                check_request = Request(
                    base + "/api/check",
                    data=b"{}",
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(check_request) as response:
                    checked = json.load(response)
                self.assertEqual(checked["summary"]["disabled"], 1)

                state_path.write_text(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "items": {
                                "microsoft/UFO": {
                                    "observed": {"mode": "release", "value": "v2"},
                                    "acknowledged": {"mode": "release", "value": "v1"},
                                }
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                ack_request = Request(
                    base + "/api/ack",
                    data=b"{}",
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(ack_request) as response:
                    acked = json.load(response)
                self.assertEqual(acked["changed"], 1)
                self.assertEqual(acked["dashboard"]["summary"]["local_updates"], 0)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)
            self.assertFalse(Registry.load(registry_path).data["items"][0]["enabled"])

    def test_scan_preview_does_not_mutate_and_apply_only_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path = root / "registry.json"
            state_path = root / "state.json"
            reports_path = root / "reports"
            config_path = root / "config.json"
            Registry.empty().save(registry_path)

            scan_root = root / "repos"
            repo = scan_root / "sample"
            repo.mkdir(parents=True)
            import subprocess

            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "remote", "add", "origin", "https://github.com/example/sample.git"],
                check=True,
            )

            server = create_server(
                registry_path,
                state_path,
                reports_path,
                port=0,
                config_path=config_path,
                metadata_cache_path=root / "cache" / "metadata.json",
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_address[1]}"
                started = self._post_json(
                    base + "/api/scan/start",
                    {"roots": [{"path": str(scan_root), "mode": "quick"}]},
                )
                job = started["job"]
                status = None
                for _ in range(100):
                    with urlopen(base + f"/api/scan/status?job={job}") as response:
                        status = json.load(response)
                    if not status["running"]:
                        break
                    time.sleep(0.02)
                self.assertIsNotNone(status)
                self.assertFalse(status["running"])
                self.assertEqual(len(status["rows"]), 1)
                self.assertEqual(status["rows"][0]["repo"], "example/sample")

                # Preview is read-only.
                self.assertEqual(len(Registry.load(registry_path).data["items"]), 0)

                applied = self._post_json(
                    base + "/api/scan/apply",
                    {"job": job, "local_paths": [status["rows"][0]["local_path"]]},
                )
                self.assertEqual(len(applied["applied"]), 1)
                registry = Registry.load(registry_path)
                self.assertEqual([item["repo"] for item in registry.data["items"]], ["example/sample"])

                with urlopen(base + "/api/settings") as response:
                    settings = json.load(response)["config"]
                self.assertTrue(settings["onboarding_complete"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_scan_cancel_endpoint_stops_running_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path = root / "registry.json"
            state_path = root / "state.json"
            reports_path = root / "reports"
            config_path = root / "config.json"
            Registry.empty().save(registry_path)

            server = create_server(
                registry_path,
                state_path,
                reports_path,
                port=0,
                config_path=config_path,
                metadata_cache_path=root / "cache" / "metadata.json",
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()

            import oss_update_watch.ui_server as ui_server

            def slow_deep_scan(*args, should_cancel=None, **kwargs):
                from oss_update_watch.scanner import ScanResult

                result = ScanResult()
                deadline = time.time() + 3
                while time.time() < deadline:
                    if should_cancel and should_cancel():
                        result.cancelled = True
                        return result
                    time.sleep(0.01)
                return result

            try:
                base = f"http://127.0.0.1:{server.server_address[1]}"
                with mock.patch.object(ui_server, "deep_scan", slow_deep_scan):
                    started = self._post_json(
                        base + "/api/scan/start",
                        {"roots": [{"path": str(root), "mode": "deep"}]},
                    )
                    job = started["job"]
                    cancelled = self._post_json(base + "/api/scan/cancel", {"job": job})
                    self.assertTrue(cancelled["cancelling"])
                    status = None
                    for _ in range(100):
                        with urlopen(base + f"/api/scan/status?job={job}") as response:
                            status = json.load(response)
                        if not status["running"]:
                            break
                        time.sleep(0.02)
                    self.assertIsNotNone(status)
                    self.assertFalse(status["running"])
                    self.assertTrue(status["cancelled"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
