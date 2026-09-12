# Fossight 1.0.0 Release Notes

**English** | [Japanese](FOSSIGHT_RELEASE_1.0.0.ja.md)

## Summary

Fossight 1.0.0 turns the original developer-local OSS watcher into a Windows distribution that can be installed and used by third parties without the source checkout or a system Python installation.

## Highlights

- First-run onboarding and prerequisite checks
- User-selected scan roots
- Quick Scan and bounded/cancellable Deep Scan
- Preview before registry mutation and selective apply
- Direct/fork remote detection and duplicate upstream consolidation
- Arbitrary-repository metadata fallback and local cache
- `%LOCALAPPDATA%\FossightData` per-user mutable data profile
- PyInstaller-packaged Python backend sidecar
- Tauri current-user NSIS installer
- Installer SHA-256 checksum
- Source-tree-free runtime with no Python/Node.js/Rust/Cargo requirement
- Missing-Git remediation inside the application
- Release artifact path/credential marker audit
- Expanded scanner, API, security, browser, upgrade, and performance validation

## Compatibility

Internal identifiers such as `oss-update-watch`, the Python module `oss_update_watch`, and the Modora module ID remain unchanged for compatibility. The user-visible product name is **Fossight**.

## Migration

Earlier developer-local registry/state/report data can be copied non-destructively into the per-user profile when the destination is empty. The short-lived `%LOCALAPPDATA%\Fossight` data layout is also migrated by copying known user-data files only; installed binaries and uninstallers are never treated as user data.

A real `0.9.1 -> 1.0.0` installer upgrade was validated with registry contents, Disabled state, scan roots, and monitoring state preserved.

## Runtime requirements

- Windows 11 x64
- Git for Windows for repository inspection
- WebView2 Runtime

Python, Node.js, Rust/Cargo, and a Fossight source checkout are not runtime requirements.

## Security / privacy

See [`FOSSIGHT_SECURITY_PRIVACY.md`](FOSSIGHT_SECURITY_PRIVACY.md). The local UI binds only to loopback. Fossight does not persist GitHub credential values. Mutable user data is outside the install tree and survives uninstall by design.

## Validation summary

- Python unit/integration suite: **75/75 PASS**
- Rust desktop tests: **5/5 PASS**
- JavaScript syntax / Rust format: **PASS**
- Browser first-run/scanner/details/responsive E2E: **PASS**
- Quick Scan 100-repository performance target: **PASS**
- Sidecar / source-tree-free release isolation: **PASS**
- NSIS install/restart/uninstall: **PASS**
- `0.9.1 -> 1.0.0` installer upgrade: **PASS**
- Release artifact checksum/version/forbidden-marker audit: **PASS**

## Known limitations

- Windows x64 only
- GitHub-focused remote discovery/update monitoring
- No automatic repository update/merge
- No dependency/SBOM/CVE/license scanning
- Installer is unsigned unless an external signing step is supplied
- A separate clean Windows VM/Sandbox was not available on the development host; source-tree-free clean-media/minimal-PATH validation was completed instead and is documented separately from a true VM run
