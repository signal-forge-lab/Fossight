# Fossight 1.0.0 Release Readiness Review

[English](FOSSIGHT_RELEASE_READINESS_1.0.0.md) | **日本語**

Date: 2026-09-12
Release candidate: `Fossight_1.0.0_x64-setup.exe`
SHA-256: `93178aadf40bf9565f26957144f49e2dd8a2ba6e50cbc1b38c6ebafd1551ba43`

## Verdict

**PASS_WITH_ENVIRONMENT_LIMITATION**

利用可能なWindows host上で実行できるimplementation、packaging、upgrade、regression、browser E2E、security/artifact、documentation gateはすべてPASSしました。未解決のP0/P1 product defectはありません。

このhostでは管理者レベルのOS feature作業なしに別clean Windows VM/Sandboxを利用できませんでした。そのため、source treeなし・clean installer media・隔離user data・Python / Node.js / Rust/Cargo / GitなしPATHによるclean-machine-equivalent検証を実施しPASSしています。これはVM実行済みとは表現しません。Git欠落時もstartup failureではなくアプリ内prerequisiteとして処理されました。

## Final review questions

1. **source checkoutなしで第三者がinstall/useできるか — Yes.** NSIS installerにTauri desktopとpackaged backend sidecarを含み、source-free release smokeと実installer E2EがPASS。
2. **Pythonは同梱されているか — Yes.** backendはPyInstaller one-file sidecarとしてpackageされ、release modeではsystem Pythonを使いません。
3. **build toolsはruntime requirementから外れているか — Yes.** Python、Node.js、Rust、CargoをPATHから除外したrelease/installer smokeがPASS。
4. **Git欠落を検出・説明できるか — Yes.** prerequisite testとinstaller E2Eで、crashせず具体的な導入案内を確認。
5. **`..\\github` 固定ではなくuser-selected rootを使うか — Yes.** 配布版はonboarding/scanner rootsをper-user configへ保存します。旧CLI defaultはdeveloper compatibilityのみ。
6. **scanは選択・preview・bounded・cancellableか — Yes.** Quick/Deep、depth/exclusion、preview-before-apply、selective apply、progress、cancelを検証済み。
7. **任意repositoryで有用なDetailsを表示できるか — Yes.** GitHub description -> README paragraph -> deterministic no-description state、cache/offline fallbackを実装。
8. **mutable user dataはinstall tree外か — Yes.** `%LOCALAPPDATA%\\FossightData` と `%LOCALAPPDATA%\\Fossight` を分離。
9. **secretはFossight管理のplaintext persistence/logへ残らないか — Yes.** auth statusはsource/stateのみ、artifactもcredential marker scanをPASS。GitHub tokenはpersistしません。
10. **clean-machine E2EはPASSか — plan-authorized clean-machine-equivalentでPass.** 真の別VM/Sandboxは利用不可であり、実施済みとは主張しません。
11. **upgradeでregistry/stateを保持するか — Yes.** 実 `0.9.1 -> 1.0.0` installer upgradeでregistry、Disabled state、scan roots、state markerを保持。
12. **uninstallがuser dataを尊重するか — Yes.** installer/upgrade E2Eでapplication binary削除とuser data保持を確認。
13. **artifact/checksumをdocumented commandから再現できるか — Yes.** `build-installer.ps1` と `test-distribution-artifacts.ps1` で生成・検証。
14. **P0/P1 issueは0か — Yes.** install/data collision、Scanner UX、Quick Scan性能、build-user path leakageを修正・再テスト済み。

## Final evidence

- Python tests: **75/75 PASS**
- Rust desktop tests: **5/5 PASS**
- JavaScript syntax: **PASS**
- Rust formatting: **PASS**
- Quick Scan 100 repositories: **3.50 s PASS**（target <5 s）
- Deep Scan first progress: **immediate PASS**
- Browser E2E: **PASS**
- Scan cancellation: **PASS**
- Sidecar standalone smoke: **PASS**
- Source-tree-free release smoke with minimal PATH: **PASS**
- NSIS install/restart/uninstall E2E: **PASS**
- `0.9.1 -> 1.0.0` installer upgrade E2E: **PASS**
- Final artifact checksum/version/forbidden-marker audit: **PASS**
- Installer Authenticode status: **NotSigned**

## Remaining external limitation

別のclean Windows VM/Sandboxが将来利用可能になれば追加のrelease-channel evidenceとして望ましいですが、これは未解決のimplementation defectではありません。

## Release recommendation

Fossight 1.0.0は、上記environment limitationを明示したうえで **unsigned Windows x64 third-party distribution candidate** としてreadyです。Code signingはcertificate/secretが提供された場合に追加できます。
