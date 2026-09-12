# Fossight 1.0 User Guide

**English** | [Japanese](FOSSIGHT_USER_GUIDE.ja.md)

## 1. What Fossight does

Fossight finds local Git repositories on Windows, resolves their GitHub upstreams, registers the OSS you use, and shows both local checkout status and upstream changes.

Fossight does not automatically pull, merge, reset, or push repositories. Scanning and checking are observational; registry changes and acknowledgements happen only through explicit user actions.

## 2. Installation

1. Run `Fossight_1.0.0_x64-setup.exe`.
2. The current-user installer normally does not require administrator privileges.
3. Launch Fossight and complete first-run setup.

Application files are installed under `%LOCALAPPDATA%\Fossight`. Mutable user data is stored separately under `%LOCALAPPDATA%\FossightData`.

### Runtime requirements

- Windows 11 x64
- WebView2 Runtime
- Git for Windows

Python, Node.js, Rust, Cargo, and a Fossight source checkout are not required.

If Git is missing, Fossight shows an actionable prerequisite message rather than failing to launch.

## 3. First-run setup

1. Click **Get started**.
2. Review Git and GitHub authentication status under **Prerequisites**.
3. Add one or more folders containing your local Git repositories.
4. Choose **Quick Scan** or **Deep Scan** for each root.
5. Click **Scan repositories**.
6. Review the preview and keep only the candidates you want to register selected.
7. Click **Add selected**.

The registry is not changed during preview.

## 4. Scanner

### Quick Scan

If the selected root is itself a Git repository, Fossight inspects that repository. Otherwise it checks direct child directories only. This is the recommended default for most repository folders.

### Deep Scan

Deep Scan recursively searches below the selected root with a bounded maximum depth. Default exclusions include `.workbridge`, `node_modules`, `.venv`, `venv`, `target`, `dist`, `build`, and `vendor`. Symlinks and junctions are not followed.

Deep Scan reports progress and can be cancelled.

### Remote resolution

- Valid GitHub `upstream` remote -> monitor upstream, `relation=\"fork\"`
- No valid upstream, but valid GitHub `origin` -> monitor origin, `relation=\"direct\"`
- No supported GitHub remote -> show a skip reason in preview

The same `owner/repo` is stored once. Multiple local checkouts are represented as `usages`.

## 5. Main window

- **Local Updates** — local checkouts behind the currently tracked upstream commit
- **Upstream Changes** — upstream values changed since the monitoring baseline
- **Attention** — states such as `Ahead` or `Diverged` that need review
- **Errors** — Git or GitHub inspection failures
- **Disabled** — registered entries excluded from upstream checks

Select a row to open **OSS Details**. Details include the description, local/upstream status, tracking mode, current value, priority, local usages, and a GitHub homepage link.

## 6. Check Updates and Acknowledge

**Check updates** observes upstream state and compares registered local checkouts with the tracked upstream commit. The first successful upstream observation becomes the baseline automatically.

If upstream changes later, the entry remains under **Upstream Changes** until you review it and use **Acknowledge changes**.

## 7. Enable / Disable

An OSS entry can be disabled from the list or Details pane. A disabled entry stays in the registry but is excluded from upstream checks. It can be enabled again at any time.

## 8. GitHub authentication

Anonymous access works for public repositories but has a lower API rate limit. Fossight detects authentication in this order:

1. `GITHUB_TOKEN`
2. `GH_TOKEN`
3. GitHub CLI (`gh auth token`)
4. anonymous

The UI exposes only the authentication method/state. Fossight does not display or persist token values.

## 9. User data and restart persistence

Default Windows data location:

```text
%LOCALAPPDATA%\FossightData\
  config.json
  registry.json
  state.json
  reports\
  cache\
  logs\
```

Scan roots, registry contents, enable/disable state, and monitoring baselines persist across restarts.

## 10. Uninstallation

Uninstalling Fossight removes application files from `%LOCALAPPDATA%\Fossight` but intentionally preserves `%LOCALAPPDATA%\FossightData` so a later reinstall can continue using the same registry.

To remove all Fossight data, uninstall the application first and then manually delete `%LOCALAPPDATA%\FossightData`.

## 11. Troubleshooting

### Git missing

Install Git for Windows and use **Retry** on the Prerequisites screen.

### GitHub rate limit / HTTP errors

Check network access. If needed, sign in with GitHub CLI or provide `GITHUB_TOKEN` / `GH_TOKEN` through the process environment.

### A repository is not found

Quick Scan checks direct children only. Use Deep Scan or add a root closer to the repository.

### No description for an unknown repository

For repositories outside the curated catalog, Fossight falls back to GitHub description, then the first useful README paragraph, then `No description available yet.` Retrieved metadata is cached and stale cache can be shown offline.

### Fossight does not launch

The distributed build does not require system Python. If reinstalling does not help, verify WebView2 Runtime, Windows Event Viewer, and the Fossight `logs` directory.

## 12. Known limitations

- Windows x64 distribution only
- Primarily GitHub-focused repository discovery and monitoring
- No automatic repository update/merge
- Not a package dependency, SBOM, CVE, or license scanner
- The 1.0.0 installer is unsigned unless a separate signing step is provided
