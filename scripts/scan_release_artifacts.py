"""Exact byte-sequence scan for release artifacts.

Used by P7 distribution QA. Avoids false positives from decoding arbitrary
binary data as UTF-16 text.
"""

from __future__ import annotations

import sys
from pathlib import Path


FORBIDDEN = (
    "C:\\Users\\",
    "github_pat_",
    "ghp_",
)


def scan(path: Path) -> list[str]:
    data = path.read_bytes()
    hits: list[str] = []
    for value in FORBIDDEN:
        if value.encode("utf-8") in data or value.encode("utf-16le") in data:
            hits.append(value)
    return hits


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: scan_release_artifacts.py <artifact> [...]", file=sys.stderr)
        return 2
    failed = False
    for raw in argv:
        path = Path(raw)
        if not path.is_file():
            print(f"MISSING {path}", file=sys.stderr)
            failed = True
            continue
        hits = scan(path)
        if hits:
            print(f"FAIL {path}: {', '.join(hits)}", file=sys.stderr)
            failed = True
        else:
            print(f"PASS {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
