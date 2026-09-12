"""PyInstaller entry point for the Fossight packaged backend sidecar."""

from oss_update_watch.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
