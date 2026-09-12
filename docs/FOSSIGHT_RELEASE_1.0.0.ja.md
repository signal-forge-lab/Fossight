# Fossight 1.0.0 リリースノート

[English](FOSSIGHT_RELEASE_1.0.0.md) | **日本語**

## Summary

Fossight 1.0.0は、開発checkout前提だったOSS watcherを、第三者がWindows上でinstallerから利用できる配布版へ移行するリリースです。

## Highlights

- First-run onboarding / prerequisite check
- user-selected scan roots
- Quick Scan / bounded Deep Scan
- Preview before registry mutation / selected apply
- direct/fork remote detection and duplicate upstream consolidation
- arbitrary repository metadata fallback/cache
- `%LOCALAPPDATA%\FossightData` user-data profile
- PyInstaller packaged Python backend sidecar
- Tauri current-user NSIS installer
- installer SHA-256 checksum
- source-tree-free runtime; no Python/Node/Rust/Cargo requirement
- missing-Git in-app remediation
- release artifact path/credential marker audit
- scanner/API/security/performance test expansion

## Compatibility

Internal identifiers such as `oss-update-watch`, Python module `oss_update_watch`, and Modora module ID remain unchanged for compatibility. User-visible product name is **Fossight（フォサイト）**.

## Migration

Earlier developer-local registry/state/reports can be copied non-destructively into the per-user profile when the destination is empty. The short-lived `%LOCALAPPDATA%\Fossight` data layout is also migrated by copying known user-data files only; installed binaries and uninstallers are never treated as user data.

## Runtime requirements

- Windows 11 x64
- Git for Windows for repository inspection
- WebView2 Runtime

Python, Node.js, Rust/Cargo, and a Fossight source checkout are not runtime requirements.

## Security / privacy

詳細は [`FOSSIGHT_SECURITY_PRIVACY.ja.md`](FOSSIGHT_SECURITY_PRIVACY.ja.md) を参照してください。Local UIはloopbackのみにbindし、FossightはGitHub credential値を保存しません。User dataはinstall tree外にあり、uninstall後も意図的に保持されます。

## Validation summary

- Python unit/integration suite: PASS
- Rust desktop tests: PASS
- Browser first-run/scanner/details/responsive E2E: PASS
- Quick Scan 100-repository performance target: PASS on the development host
- sidecar / release isolation: PASS
- NSIS install/restart/uninstall: PASS
- release artifact forbidden-marker scan: PASS
- 0.9.1 -> 1.0.0 real installer upgrade: PASS; registry, Disabled state, scan roots, state marker, and uninstall-retained user data were preserved
- final 1.0.0 artifact checksum/version/forbidden-marker audit: PASS

## Known limitations

- Windows x64 only
- GitHub-focused remote detection/update monitoring
- no automatic repository update/merge
- no dependency/SBOM/CVE/license scanning
- unsigned installer unless a separate signing step is supplied
- no separate Windows Sandbox/VM was available on the development host; the release process therefore records source-tree-free clean-media/minimal-PATH validation separately from a true VM run
