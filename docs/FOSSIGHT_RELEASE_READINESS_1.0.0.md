# Fossight 1.0.0 Release Readiness Review

Date: 2026-09-12
Release candidate: `Fossight_1.0.0_x64-setup.exe`
SHA-256: `93178aadf40bf9565f26957144f49e2dd8a2ba6e50cbc1b38c6ebafd1551ba43`

## Verdict

**PASS_WITH_ENVIRONMENT_LIMITATION**

All implementation, packaging, upgrade, regression, browser E2E, security/artifact, and documentation gates that can be executed on the available Windows host pass. No P0/P1 product defect remains.

A separate clean Windows VM/Sandbox is not available on this host without administrator-level OS feature work. The execution plan explicitly requires the strongest clean-machine-equivalent validation when such an isolated environment is unavailable and prohibits representing that fallback as a VM run. That fallback passed using clean installer media, isolated user data, no source tree, and a runtime PATH without Python, Node.js, Rust/Cargo, or Git. Missing Git was handled in-app rather than causing startup failure.

## Final review questions

1. **Can a third party install/use Fossight without the source checkout? — Yes.** The NSIS installer contains the Tauri desktop and packaged backend sidecar; source-free release smoke and real installer E2E pass.
2. **Is Python bundled? — Yes.** The Python backend is packaged as a PyInstaller one-file sidecar. System Python is not used in release mode.
3. **Are build tools absent from runtime requirements? — Yes.** Python, Node.js, Rust and Cargo were removed from the runtime PATH during successful release/installer smoke tests.
4. **Is missing Git detected and explained? — Yes.** Prerequisite tests and installer E2E confirm actionable in-app remediation instead of a crash.
5. **Is `..\\github` replaced by user-selected roots? — Yes.** The distribution path uses onboarding/scanner roots stored in per-user config. The old CLI `discover` default remains only as a developer compatibility path.
6. **Are scans selected, previewed, bounded, and cancellable? — Yes.** Quick/Deep choice, bounded depth/exclusions, preview-before-apply, selective apply, progress, and cancel paths are tested.
7. **Can arbitrary repositories show useful Details? — Yes.** Metadata fallback uses GitHub description, then README paragraph, then deterministic no-description state with cache/offline fallback.
8. **Is mutable user data outside the install tree? — Yes.** Windows mutable data is `%LOCALAPPDATA%\\FossightData`; NSIS application files are under `%LOCALAPPDATA%\\Fossight`.
9. **Are secrets absent from persistent plaintext data/logs? — Yes for Fossight-managed persistence.** Auth status exposes source/state but not token values; release artifacts pass forbidden credential-marker scans. Fossight does not persist GitHub tokens.
10. **Does clean-machine E2E pass? — Pass under the plan-authorized clean-machine-equivalent fallback; a true separate VM/Sandbox run was not available and is not claimed.** Clean-media/minimal-PATH install, launch, restart persistence and uninstall all pass.
11. **Does upgrade preserve registry/state? — Yes.** A real 0.9.1 -> 1.0.0 installer upgrade preserved registry contents, Disabled state, scan roots and state markers.
12. **Does uninstall respect user data? — Yes.** Installer and upgrade E2E both verify that application binaries are removed while isolated user data remains.
13. **Are artifacts/checksums reproducible from documented commands? — Yes.** `build-installer.ps1` produces the installer and matching `.sha256`; `test-distribution-artifacts.ps1` verifies checksum and version consistency.
14. **Are P0/P1 issues zero? — Yes.** Findings discovered during P6/P7 (install/data collision, Scanner UX exits, Quick Scan performance, build-user path leakage) were corrected and retested.

## Final evidence

- Python tests: **75/75 PASS**
- Rust desktop tests: **5/5 PASS**
- JavaScript syntax: **PASS**
- Rust formatting: **PASS**
- Quick Scan 100 repositories: **3.50 s PASS** (target <5 s)
- Deep Scan first progress: **immediate PASS**
- Browser E2E: **PASS** for first-run onboarding, prerequisites, root management, Quick/Deep choice, preview/apply, Details/homepage, Enable/Disable, Check Updates, restart persistence, keyboard selection, manual-picker fallback, Scanner close and narrow-window drawer
- Scan cancellation: **PASS**
- Sidecar standalone smoke: **PASS**
- Source-tree-free release smoke with minimal PATH: **PASS**
- NSIS install/restart/uninstall E2E: **PASS**
- 0.9.1 -> 1.0.0 installer upgrade E2E: **PASS**
- Final artifact checksum/version/forbidden-marker audit: **PASS**
- Installer Authenticode status: **NotSigned** (documented optional external signing step)

## Remaining external limitation

An actual separate clean Windows VM/Sandbox run remains desirable release-channel evidence if such an environment is later made available. It is not an unresolved implementation defect and no new engineering work is required for the requested distribution scope.

## Release recommendation

Fossight 1.0.0 is ready as an **unsigned Windows x64 third-party distribution candidate**, with the environment limitation above stated explicitly. Code signing may be added later when a certificate/secret is supplied.
