"""P7 scanner performance smoke benchmark."""

from __future__ import annotations

import subprocess
import tempfile
import time
from pathlib import Path

from oss_update_watch.scanner import deep_scan, quick_scan


def init_repo(path: Path, name: str) -> None:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(
        ["git", "-C", str(path), "remote", "add", "origin", f"https://github.com/example/{name}.git"],
        check=True,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="fossight-perf-") as tmp:
        root = Path(tmp)
        quick_root = root / "quick"
        quick_root.mkdir()
        for index in range(100):
            init_repo(quick_root / f"repo-{index:03d}", f"repo-{index:03d}")

        started = time.perf_counter()
        result = quick_scan(quick_root)
        elapsed = time.perf_counter() - started
        if result.repositories_found != 100:
            raise RuntimeError(f"expected 100 repositories, got {result.repositories_found}")
        if elapsed >= 5.0:
            raise RuntimeError(f"Quick Scan target exceeded: {elapsed:.3f}s >= 5s")

        deep_root = root / "deep"
        current = deep_root
        for index in range(80):
            current = current / f"d{index:03d}"
            current.mkdir(parents=True)
        callbacks: list[float] = []
        deep_started = time.perf_counter()

        def on_progress(_progress) -> None:
            callbacks.append(time.perf_counter() - deep_started)

        deep_scan(deep_root, max_depth=80, progress=on_progress, progress_every=1)
        first_progress = callbacks[0] if callbacks else float("inf")
        if first_progress >= 1.0:
            raise RuntimeError(f"Deep Scan progress target exceeded: {first_progress:.3f}s >= 1s")

        print(f"PASS Quick Scan 100 repos: {elapsed:.3f}s (<5s)")
        print(f"PASS Deep Scan first progress: {first_progress:.3f}s (<1s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
