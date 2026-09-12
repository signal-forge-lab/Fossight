# Fossight Windows Packaging

[English](FOSSIGHT_PACKAGING.md) | **日本語**

## Runtime architecture

Windows配布版は2つの実行ファイルで構成します。

```text
Fossight desktop (Tauri/WebView2)
        |
        +-- fossight-backend.exe (PyInstaller one-file sidecar)
                |
                +-- Python stdlib HTTP backend
                +-- Fossight HTML/CSS/JS assets
                +-- curated OSS summary catalog
```

既存backendはPython標準ライブラリ中心で構成されているため、P5ではPyInstaller one-file sidecarを採用しました。backend architectureを大きく変えずに自己完結型へできます。Pythonは**build時のみの依存**です。

Release buildはsystem Pythonを探索・起動しません。Debug buildだけは開発用途のためsource tree/system Python経路を残します。

## Build prerequisites

Build machineでのみ必要です。

- Windows x64 + Rust/MSVC toolchain
- Python 3.11+
- PyInstaller 6.x
- WebView2/Tauri build prerequisites
- source/build操作用Git

利用者はPython、Rust/Cargo、Node.js、Fossight source treeを必要としません。Gitはrepository inspectionの機能要件として残り、見つからない場合はアプリ内で対処方法を表示します。

Tauriのcurrent-user NSIS installerはapplication binaryを `%LOCALAPPDATA%\Fossight` に配置します。変更可能なFossight dataは `%LOCALAPPDATA%\FossightData` に分離します。Fossight 0.9.1以降は、以前の `%LOCALAPPDATA%\Fossight` data layoutから既知のuser-data fileだけをコピー移行でき、installed executableやuninstallerは移行対象にしません。

## Sidecar build

```powershell
./build-sidecar.ps1
./test-sidecar.ps1
```

`build-sidecar.ps1` はTauri bundler用に `src-tauri/binaries/` 配下へtarget-triple付きbinaryを生成します。生成EXEはGit管理外です。

## Developer release build

```powershell
./desktop-build.ps1
./test-release-desktop.ps1
```

`desktop-build.ps1` はsidecarとoptimized Tauri executableをbuildし、raw release executableの隣へ `fossight-backend.exe` を配置します。

`test-release-desktop.ps1` は2つのEXEだけを隔離directoryへコピーし、Python / Node / Rust/Cargo / Gitを除外した最小PATHで起動します。Fossightがsource treeなしで起動でき、Git欠落がstartup failureではなくprerequisiteとして扱われることを確認します。

## NSIS installer build

```powershell
./build-installer.ps1
./test-installer.ps1
```

`build-installer.ps1` はsidecarをbuildし、Tauri NSIS bundlerを実行してinstallerを `dist/` へコピーし、対応する `.sha256` を生成します。

Release Rust buildではsource checkoutとbuild user profileに `--remap-path-prefix` を適用し、Cargo dependencyのpanic/source metadataから開発者の絶対pathがdesktop executableへ混入することを防ぎます。

`test-installer.ps1` は実際のcurrent-user installerを次の流れでE2E検証します。

```text
silent install
-> packaged sidecarで起動
-> settings保存
-> 終了・再起動
-> silent uninstall
-> user data保持確認
```

testではPython / Node / Rust/Cargo / Gitを除外した最小PATHを使用し、user-data directoryも開発者profileから隔離します。

最終artifact確認:

```powershell
./test-distribution-artifacts.ps1
```

checksum/version整合性を確認し、installer、desktop EXE、sidecarを開発者path・credential markerについてscanします。Authenticode状態も報告し、未署名候補は `NotSigned` と表示します。

## Startup diagnostics

packaged backendがない、または起動できない場合、release launcherは具体的なerrorを表示します。`FOSSIGHT_BACKEND_EXE` はdeveloper/test用override、`FOSSIGHT_DATA_DIR` はuser-data location overrideです。

## Security and privacy

- sidecar UI/APIは `127.0.0.1` のみにbind
- user registry/state/cache/report dataはbundleしない
- GitHub token値をpackage artifactやstatus APIへ書き込まない
- curated catalogはread-only package data
- arbitrary repository metadataはuser data directoryへcache
- Windows mutable dataは `%LOCALAPPDATA%\FossightData`、installer directory `%LOCALAPPDATA%\Fossight` にはapplication fileのみ配置
