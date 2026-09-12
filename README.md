# Fossight

**Fossight（フォサイト）** は、Windows 上で使用している GitHub OSS を台帳化し、ローカル checkout と upstream の差分や更新を追跡するローカル管理ツールです。

名称は **FOSS + Sight** を組み合わせた造語で、OSS を「見る・俯瞰する・監視する」という役割を表します。同時に **Foresight（先を見通す）** の響きも重ねています。正式なカタカナ読みは **フォサイト** です。詳細は `docs/NAMING.md` を参照してください。

## Windows配布版の利用

通常の利用者は `Fossight_<version>_x64-setup.exe` をインストールして起動します。Python / Rust / Cargo / Node.js やFossightのソースcheckoutは不要です。ローカルrepositoryの判定には **Git for Windows** を使用するため、Gitがない場合は初回画面に導入案内を表示します。

初回起動では、repositoryを置いているフォルダを選び、`Quick Scan` または `Deep Scan` を実行します。結果はpreviewされ、選択した候補だけが台帳へ追加されます。Fossightがrepositoryを自動更新・mergeすることはありません。

Windows配布版の変更可能データは `%LOCALAPPDATA%\FossightData` に保存され、アプリ本体の `%LOCALAPPDATA%\Fossight` とは分離されています。詳しい操作は `docs/FOSSIGHT_USER_GUIDE.md`、privacy/securityは `docs/FOSSIGHT_SECURITY_PRIVACY.md` を参照してください。

## 方針

- **1 OSS = 1 registry entry**。複数の自作ツールから使っていても重複登録しません。
- 利用箇所は `usages` に `project` と `relation` (`direct` / `fork` / `reference`) を追加します。
- `check` は upstream の最新値を観測し、最後に `ack` した値との差分だけを通知します。
- `ack` するまで UPDATE は残ります。定期実行で通知を取りこぼしません。
- 自動更新・自動 merge はしません。更新検知とレビュー判断を分離します。
- Python 標準ライブラリのみで動作し、生成 JSON は将来の専用 UI からそのまま読めます。

## 構成

```text
%LOCALAPPDATA%\Fossight\       # current-user NSIS install先
%LOCALAPPDATA%\FossightData\   # config / registry / state / reports / cache

source checkout（開発者向け）
├─ src/oss_update_watch/        # 監視コア / CLI / local UI
├─ src-tauri/                   # Tauri desktop shell / bundle config
├─ tests/                       # unittest / integration tests
├─ build-sidecar.ps1            # packaged Python backend
├─ build-installer.ps1          # NSIS + SHA-256
└─ run.ps1                      # developer CLI入口
```

## 基本操作

### OSSを追加

```powershell
.\run.ps1 add microsoft/UFO --project ufo --relation direct --path ..\github\UFO
```

fork の upstream を追う場合:

```powershell
.\run.ps1 add microsoft/UFO --project my-ufo-fork --relation fork --path ..\github\my-ufo-fork
```

別ツールから参照しているだけの場合:

```powershell
.\run.ps1 add microsoft/UFO --project automation-research --relation reference
```

同じ `owner/repo` は1件に統合され、`usages` だけ増えます。

### ローカルclone/forkを発見

配布版ではMain画面の **Scanner** を使用します。フォルダを選ぶとpreviewが表示され、チェックしたrepositoryだけを追加できます。Quick Scanは指定rootまたは直下だけ、Deep Scanは除外ルールと最大depthを適用した再帰探索です。

以下のCLI `discover` はsource checkoutを使う開発者向け互換入口です。

既定では sibling の `..\github` を走査します。**確認だけで台帳は変更しません**。

```powershell
.\run.ps1 discover
```

確認した候補をまとめて追加する場合だけ `--apply` を付けます。

```powershell
.\run.ps1 discover --apply
```

`upstream` remote がある repository は `fork`、なければ `origin` を `direct` として候補化します。

### 一覧

```powershell
.\run.ps1 list
```

### 更新確認

```powershell
.\run.ps1 check
```

初回の成功チェックでは現在のupstream値を自動的にbaselineとして保存します。手動の `ack --all` は不要です。

以降、upstreamがbaselineから変化すると `Upstream Changes` に表示されます。内容を確認した後、UIの `Acknowledge changes` またはCLIの `ack` で確認済みにできます。`Local Updates` はこのbaselineとは独立して、ローカルcheckoutが現在のupstreamよりBehindかどうかを示します。

```powershell
.\run.ps1 ack microsoft/UFO
```

### 削除

1つの利用関係だけ外す場合:

```powershell
.\run.ps1 remove microsoft/UFO --project automation-research
```

最後の `usage` を削除すると OSS entry 自体も消えます。全利用箇所を一括削除する場合:

```powershell
.\run.ps1 remove microsoft/UFO --all
```

## tracking mode

### Check semantics (v0.4.0)

`Check updates` now reports two independent concepts:

- `Local Updates`: registered local checkouts whose HEAD is behind the currently tracked upstream commit.
- `Upstream Changes`: upstream values that changed after the monitoring baseline was established.

The first successful observation is automatically stored as the baseline. A manual baseline acknowledgement is no longer required for first-time setup. Local checkout status is reported as `Latest`, `Behind`, `Ahead`, `Diverged`, or `N/A/Error` without changing the working tree.

> v0.3.1: 機械検出したOSSの既定は `auto` です。`auto` は GitHub Release → Tag → default branch の順で利用可能な更新基準を選びます。Releaseを持たないrepositoryはErrorではなくTag/branch追跡へ自動的に切り替わります。明示的に `--track release|tag|branch` を指定した場合はその方式を固定します。


既定は `release` です。GitHub の latest stable release（draft / prerelease を除外）を追跡します。

release を作らないOSSでは tag または branch を指定できます。

```powershell
.\run.ps1 add owner/repo --project tool-a --track tag
.\run.ps1 add owner/repo --project tool-a --track branch --branch main
```

## GitHub API

公開 repository は認証なしで確認できます。登録数が多く GitHub の未認証 rate limit に達する場合は、実行環境から `GITHUB_TOKEN` または `GH_TOKEN` を渡すか、GitHub CLI (`gh`) のloginを利用できます。Fossightはtoken値をconfig/status APIへ保存・表示しません。

## 定期実行

Windows タスクスケジューラには `check.ps1` を登録できます。曜日・時刻は運用が固まってから決めればよく、このリポジトリ自身はスケジュールを持ちません。

`run.ps1 check` の終了コード:

- `0`: 全件 OK
- `1`: Local update、Upstream change、またはDiverged等のAttentionあり
- `2`: 1件以上 ERROR

`check.ps1` はタスクスケジューラ向け入口なので、`0` と `1` を正常終了 `0` にまとめます。`2` を含むその他の異常終了コードはそのまま返します。

新しい clone / fork を1件だけ登録する場合は、その repository を直接 `discover --apply` できます。

```powershell
.\run.ps1 discover ..\github\new-tool --apply
```

## テスト

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m unittest discover -s tests -v
```

## Desktop app (Tauri + WebView2)

ブラウザ版と同じ Python watcher / HTML / CSS / JavaScript を再利用し、Tauri 2 + WebView2 を薄い単体ウィンドウ shell として使用します。配布版ではPython backendをPyInstaller one-file sidecarとして同梱するため、利用者のsystem Pythonは使用しません。Rust側にはOSS監視ロジックを重複実装せず、packaged backendの起動・ready待ち・WebView window生成・終了時cleanupだけを持たせています。

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
        +-- enabled / disabled state
```

起動:

```powershell
.\desktop.ps1
```

開発checkoutでは必要に応じてsidecarとrelease buildを生成し、`src-tauri\target\release\oss-update-watch-desktop.exe` を起動します。デスクトップ版の内部 HTTP port は `18766-18865` から空きを自動選択するため、ブラウザ版の既定 `18765` や他ツールと競合しません。

明示的に build だけ行う場合:

```powershell
.\desktop-build.ps1
```

Windows installerを生成する場合:

```powershell
.\build-installer.ps1
.\test-installer.ps1
.\test-distribution-artifacts.ps1
```

詳細は `docs/FOSSIGHT_PACKAGING.md` を参照してください。

## Modora

`modora.module.json` と `modora-adapter.mjs` は tool-owned の Modora module 定義です。Modora core 側への専用分岐は不要です。`open` / `status` / `signals` を公開し、Modora から単体デスクトップウィンドウを開けます。

## Local management UI

The registry can also be managed from a local-only web UI. It binds to `127.0.0.1:18765` by default and is not exposed to the LAN.

```powershell
.\ui.ps1
```

or:

```powershell
.\run.ps1 ui
```

The UI provides repository search, status/relation filters, summary counts, update checks, and per-OSS enable/disable toggles. Each registered OSS also loads its Japanese description from `docs/oss-summary-catalog.md`: hovering or keyboard-focusing a repository shows a short tooltip, while selecting a row pins the full description and status metadata in a resizable right-hand details pane. The details pane also links directly to the selected OSS repository homepage on GitHub. At narrower window widths the details pane becomes a slide-in drawer. Disabling an OSS keeps it in `oss-registry.json` but excludes it from GitHub update checks.

The same state can be changed from the CLI:

```powershell
.\run.ps1 disable owner/repo
.\run.ps1 enable owner/repo
```

Use another local port when needed:

```powershell
.\run.ps1 ui --port 18766
```
