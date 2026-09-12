# Fossight 1.0 ユーザーガイド

[English](FOSSIGHT_USER_GUIDE.md) | **日本語**

## 1. Fossightとは

Fossight（フォサイト）は、Windows上のローカルGit repositoryを見つけ、対応するGitHub upstreamを台帳化して、ローカルcheckoutとupstreamの状態を確認するツールです。

Fossightはrepositoryを自動更新・merge・pushしません。ScanとCheckは観測、ApplyとAcknowledgeはユーザーが明示して行う操作です。

## 2. インストール

1. `Fossight_1.0.0_x64-setup.exe` を実行します。
2. current-user installなので通常は管理者権限を必要としません。
3. 起動後、初回Setupを進めます。

Fossight本体は `%LOCALAPPDATA%\Fossight`、ユーザーデータは `%LOCALAPPDATA%\FossightData` に保存されます。

### 必要なもの

- Windows 11 x64
- WebView2 Runtime（通常のWindows 11環境に含まれます）
- Git for Windows

Python、Node.js、Rust、Cargo、Fossightのsource checkoutは不要です。

Gitが見つからない場合、FossightはクラッシュせずPrerequisitesに導入案内を表示します。

## 3. 初回Setup

1. `Get started` を押します。
2. PrerequisitesでGitとGitHub auth状態を確認します。
3. repositoryを置いているフォルダを追加します。
4. rootごとにQuick Scan / Deep Scanを選択します。
5. `Scan repositories` を実行します。
6. Previewで候補を確認し、登録したい項目だけチェックします。
7. `Add selected` を押します。

Previewまではregistryを変更しません。

## 4. Scanner

### Quick Scan

指定したフォルダ自身がGit repositoryならその1件を確認します。そうでなければ直下のフォルダだけを確認します。通常はこちらを推奨します。

### Deep Scan

指定root以下を再帰探索します。最大depthを持ち、`.workbridge`, `node_modules`, `.venv`, `venv`, `target`, `dist`, `build`, `vendor` 等を既定で除外します。symlink/junctionを追跡しないため循環探索しません。

### remote判定

- 有効なGitHub `upstream` がある: upstreamを監視対象、relation=`fork`
- upstreamがなく有効なGitHub `origin` がある: originを監視対象、relation=`direct`
- GitHub remoteがない: Previewでskip理由を表示

同じ`owner/repo`は1 OSSへ統合され、複数checkoutは`usages`として保持されます。

## 5. Main画面

- **Local Updates**: local checkoutが現在のupstream commitよりbehindしているもの
- **Upstream Changes**: baseline以降にupstream側の監視値が変化したもの
- **Attention**: Ahead / Divergedなどレビューが必要なlocal状態
- **Errors**: Git/GitHub取得に失敗したもの
- **Disabled**: 台帳には残すがCheck対象外にしたもの

行を選択するとOSS Detailsを表示します。Detailsには説明、Local/Upstream状態、tracking、current値、priority、local usage、GitHub homepage linkが表示されます。

## 6. Check UpdatesとAcknowledge

`Check updates` はupstreamを観測し、local checkoutとの差を計算します。初回成功時は現在値をbaselineとして保存します。

その後upstreamが変化すると`Upstream Changes`に残ります。確認後に`Acknowledge changes`を押すと、その値を確認済みbaselineとして保存します。

## 7. Enable / Disable

Detailsまたは一覧からOSSをDisableできます。Disableしてもregistryから削除されず、upstream Checkだけから除外されます。再度Enableできます。

## 8. GitHub認証

公開repositoryはanonymousでも利用できますが、GitHub API rate limitは小さくなります。Fossightは次の順で利用可能な認証を検出します。

1. `GITHUB_TOKEN`
2. `GH_TOKEN`
3. GitHub CLI (`gh auth token`)
4. anonymous

UIには認証**方法**だけを表示し、token値は表示・保存しません。

## 9. データと再起動

Windowsの既定データ先:

```text
%LOCALAPPDATA%\FossightData\
  config.json
  registry.json
  state.json
  reports\
  cache\
  logs\
```

再起動してもscan roots、registry、Enable/Disable、baseline/stateは保持されます。

## 10. アンインストール

アプリ本体は `%LOCALAPPDATA%\Fossight` から削除されます。ユーザーデータ `%LOCALAPPDATA%\FossightData` は意図的に保持します。再インストール時に以前の台帳を継続利用できます。

完全にデータも消す場合は、Fossightをアンインストールした後にユーザー自身で `%LOCALAPPDATA%\FossightData` を削除してください。

## 11. Troubleshooting

### Git missing

Git for Windowsをインストールし、FossightのPrerequisitesで`Retry`します。

### GitHub rate limit / HTTP error

ネットワークを確認し、必要ならGitHub CLIでloginするか`GITHUB_TOKEN` / `GH_TOKEN`を実行環境へ設定します。

### repositoryが見つからない

Quick Scanは直下のみです。repositoryが深い階層にある場合はDeep Scanへ切り替えるか、より近いrootを追加します。

### unknown repositoryの説明がない

Fossightはcurated summaryがない場合、GitHub description、READMEの最初の有用な段落、最後に`No description available yet.`の順でfallbackします。取得済みmetadataはcacheされ、offline時はstale cacheを利用できます。

### Fossightが起動しない

配布版はsystem Pythonを必要としません。再インストールしても改善しない場合は、WebView2 RuntimeとWindows Event Viewer、Fossightの`logs`ディレクトリを確認してください。

## 12. Known limitations

- Windows x64配布のみ
- GitHub repositoryを主対象とする
- 自動update/merge機能なし
- package/SBOM/CVE/license scannerではない
- installerは1.0.0時点でcode signingなし
