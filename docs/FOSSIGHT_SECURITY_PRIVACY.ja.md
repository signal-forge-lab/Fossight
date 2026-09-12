# Fossight セキュリティとプライバシー

[English](FOSSIGHT_SECURITY_PRIVACY.md) | **日本語**

## Local-first model

FossightのUI/backendは`127.0.0.1`だけにbindし、LANへ公開しません。registry/state/reports/cacheはWindows user profile内の`%LOCALAPPDATA%\FossightData`へ保存します。

## Network access

ネットワーク通信は主にGitHub repository metadata/update確認に使用します。Scanner自体はlocal Git checkoutとremote URLを読み取ります。

## GitHub credentials

Fossightは`GITHUB_TOKEN`、`GH_TOKEN`、またはGitHub CLIの認証を利用できますが、token値を`config.json`、registry、status API、release artifactへ書き込みません。UIは`anonymous` / `gh_cli` / 環境変数名のようなauth sourceだけを表示します。

## Repository mutation policy

ScannerとLocal status比較はworking treeを変更しません。Quick/Deep Scanはremoteを観測するだけで、checkout、merge、pull、push、resetを行いません。registry mutationはPreview後の`Add selected`に限定されます。

## API boundary

- bind: `127.0.0.1` only
- JSON request body size上限あり
- non-JSON / malformed / oversized requestを拒否
- CSP / nosniff / no-referrer / no-store系security headerを設定
- sidecar portはlocalhostの空きportを動的選択

## Packaged artifacts

Release QAではinstaller、desktop EXE、sidecarをbyte-level scanし、開発者固有pathや代表的なGitHub token prefixが含まれないことを確認します。Rust release buildにはpath remappingを適用し、Cargo registryのbuild-user absolute pathをartifactから除去します。

## User-data retention

アプリ本体のinstall先 `%LOCALAPPDATA%\Fossight` とユーザーデータ `%LOCALAPPDATA%\FossightData` は分離しています。アンインストールではユーザーデータを保持します。完全削除はユーザーが明示して行います。

## Metadata cache

未知OSSのGitHub description/README由来summaryはlocal cacheへ保存されます。offline時は既存cacheを表示できます。LLMサービスへの送信はruntime要件ではありません。

## Code signing

Fossight 1.0.0 release candidateはunsigned installerとして検証されています。署名を行う場合は外部のcode-signing certificate/secretが必要です。証明書や秘密鍵をrepositoryへ保存しないでください。
