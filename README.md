# Fossight

**English** | [Japanese](README.ja.md)

**Fossight** is a local Windows application for cataloging the GitHub open-source software you actually use, comparing local checkouts with their upstreams, and monitoring upstream changes without modifying repositories automatically.

The name combines **FOSS + Sight** and also echoes **Foresight**: keeping the open-source software you depend on visible before unnoticed drift becomes maintenance debt. The official Japanese reading is **フォサイト (Fosaito)**. See [`docs/NAMING.md`](docs/NAMING.md).

## Windows distribution

Most users should install `Fossight_<version>_x64-setup.exe`. The packaged application does not require Python, Rust, Cargo, Node.js, or a Fossight source checkout. **Git for Windows** is required for local repository inspection; if Git is unavailable, Fossight shows an actionable prerequisite message instead of crashing.

On first launch, select one or more folders that contain Git repositories and run **Quick Scan** or **Deep Scan**. Fossight previews all discoveries first and adds only the candidates you explicitly select. It never automatically pulls, merges, resets, or pushes repositories.

Mutable Windows data is stored in `%LOCALAPPDATA%\FossightData`, separate from the application installation at `%LOCALAPPDATA%\Fossight`.

Documentation:

- [User Guide](docs/FOSSIGHT_USER_GUIDE.md) / [Japanese](docs/FOSSIGHT_USER_GUIDE.ja.md)
- [Security and Privacy](docs/FOSSIGHT_SECURITY_PRIVACY.md) / [Japanese](docs/FOSSIGHT_SECURITY_PRIVACY.ja.md)
- [Packaging and Release](docs/FOSSIGHT_PACKAGING.md) / [Japanese](docs/FOSSIGHT_PACKAGING.ja.md)
- [1.0.0 Release Notes](docs/FOSSIGHT_RELEASE_1.0.0.md) / [Japanese](docs/FOSSIGHT_RELEASE_1.0.0.ja.md)

## Core principles

- **One upstream OSS = one registry entry.** Multiple local projects using the same upstream become multiple `usages`, not duplicate records.
- Each usage records a `project` and `relation` (`direct`, `fork`, or `reference`).
- `Check updates` observes upstream state and local checkout state independently.
- The first successful upstream observation establishes the monitoring baseline automatically.
- Upstream changes remain visible until acknowledged.
- Fossight detects changes; it does **not** automatically update or merge repositories.

## Runtime layout

```text
%LOCALAPPDATA%\Fossight\       # current-user NSIS installation
%LOCALAPPDATA%\FossightData\   # config / registry / state / reports / cache / logs

source checkout (developers)
├─ src/oss_update_watch/        # watcher core / CLI / local UI
├─ src-tauri/                   # Tauri desktop shell / bundle config
├─ tests/                       # unit and integration tests
├─ build-sidecar.ps1            # packaged Python backend
├─ build-installer.ps1          # NSIS + SHA-256
└─ run.ps1                      # developer CLI entry point
```

## Scanner

The distributed app uses the **Scanner** in the main window.

- **Quick Scan** checks the selected root itself if it is a Git repository; otherwise it checks direct child directories only.
- **Deep Scan** recursively searches below the selected root with a bounded depth, exclusions, progress reporting, cancellation, and no symlink/junction traversal.

For each repository, Fossight resolves remotes as follows:

1. A valid GitHub `upstream` remote wins and is registered as `relation=\"fork\"`.
2. Otherwise, a valid GitHub `origin` is registered as `relation=\"direct\"`.
3. Repositories without a supported GitHub remote remain visible in the preview with a skip reason.

Preview is read-only. The registry changes only after **Add selected**.

## Update semantics

`Check updates` reports two separate concepts:

- **Local Updates** — registered local checkouts whose HEAD is behind the currently tracked upstream commit.
- **Upstream Changes** — upstream values that changed after the monitoring baseline was established.

Local status can be `Latest`, `Behind`, `Ahead`, `Diverged`, `N/A`, or `Error` without changing the working tree.

New discoveries default to `auto` tracking, which selects the best available upstream signal in this order:

```text
GitHub Release -> Tag -> default branch
```

Explicit `release`, `tag`, and `branch` tracking remain available through the developer CLI.

## GitHub authentication

Public repositories can be checked anonymously. When authentication is available, Fossight detects it in this order:

1. `GITHUB_TOKEN`
2. `GH_TOKEN`
3. GitHub CLI (`gh auth token`)
4. anonymous mode

Fossight displays the authentication **source/state**, not the token value, and does not persist GitHub tokens in its configuration or registry.

## Developer CLI

The CLI remains available for source-checkout workflows:

```powershell
.\run.ps1 add microsoft/UFO --project ufo --relation direct --path ..\github\UFO
.\run.ps1 discover
.\run.ps1 discover --apply
.\run.ps1 list
.\run.ps1 check
.\run.ps1 ack microsoft/UFO
.\run.ps1 disable owner/repo
.\run.ps1 enable owner/repo
```

The legacy `discover` command defaults to sibling `..\github` for developer compatibility. Distributed Fossight uses user-selected scanner roots instead.

## Desktop architecture

```text
Tauri / WebView2 window
        |
        v
dynamic 127.0.0.1 port
        |
        v
packaged fossight-backend.exe
        |
        +-- %LOCALAPPDATA%\FossightData\registry.json
        +-- GitHub update checks
        +-- local Git inspection
```

Release builds bundle the Python backend as a PyInstaller one-file sidecar. System Python is not used in release mode.

## Build and test

Python tests:

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m unittest discover -s tests -v
```

Desktop release build:

```powershell
.\desktop-build.ps1
```

Windows installer and distribution checks:

```powershell
.\build-installer.ps1
.\test-installer.ps1
.\test-distribution-artifacts.ps1
```

## Local web UI

The same registry can be managed from a local-only web UI bound to `127.0.0.1`:

```powershell
.\ui.ps1
```

or:

```powershell
.\run.ps1 ui
```

The UI provides search, filters, status summaries, update checks, enable/disable controls, repository Details, GitHub homepage links, and responsive drawer behavior. Repository descriptions are loaded from [`docs/oss-summary-catalog.md`](docs/oss-summary-catalog.md), with runtime metadata fallback for repositories not present in the curated catalog.

## Modora

`modora.module.json` and `modora-adapter.mjs` expose Fossight as a tool-owned Modora module with `open`, `status`, and `signals` capabilities. The stable internal module ID remains `oss-update-watch` for compatibility.
