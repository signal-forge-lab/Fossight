# Git運用とPublic / Private分離

[English](GIT_WORKFLOW.md) | [日本語](GIT_WORKFLOW.ja.md)

Fossightでは、Git branchは**開発工程の分離**に使用し、秘密情報と公開コードの分離には使用しません。

## Branch構成

```text
main
  ↑
develop
  ↑
feature/*
```

- `main`: 安定版。常に公開可能な状態を維持します。
- `develop`: 開発中の統合branch。ただし内容は公開されても問題ないものだけを置きます。
- `feature/*`: `develop`から作成する短命な機能branch。レビュー後に`develop`へ統合します。
- release時は、テストと公開安全監査を通過した`develop`を`main`へ昇格します。

緊急修正が必要な場合は、必要に応じて`main`から`hotfix/*`を作成できます。

## Public / Privateはbranchで分けない

このPublic repositoryのbranchを、secret、PC固有設定、内部専用コード、内部専用履歴の置き場所として使用しません。

用途ごとに次の境界を使用します。

| 分離対象 | 方法 |
| --- | --- |
| 安定版 / 開発版 | Git branch |
| 機能A / 機能B | Git branch |
| API Key / Token / Private Key | SOPS等の外部Secret Store。Gitへcommitしない |
| PC固有設定 | `.gitignore`対象のlocal config |
| 内部専用コード / 文書 | 別Private Repository |
| build生成物 | `.gitignore` / Release artifact |

将来Private repositoryが必要になった場合は、別のPrivate GitHub Repositoryを`private` remoteとして追加できます。Public `origin`へpush可能なbranchにprivate情報をcommitしてはいけません。

## Local専用ファイル

次のようなものはPublic履歴へ入れません。

```text
.env
.env.*
secrets/
local/
*.key
*.pem
*.p12
*.pfx
local-config.json
config.local.json
*.local.json
```

一方、公開用templateはGit管理できます。

```text
.env.example
config.example.json
```

## 公開ドキュメント規約

- 標準ファイル名は英語版とします。例: `README.md`
- 日本語版は`.ja.md`とします。例: `README.ja.md`
- Orchestrator実行ログ、local execution evidence、開発PC固有メモなどは公開ドキュメントに含めません。

## `origin`へpushする前の確認

最低限、次を実施します。

1. 対象branchとremoteを確認する。
2. `git status`とstage済みdiffをレビューする。
3. 実ユーザー名、実PC絶対path、account識別子、token、key、private registry dataがstageされていないことを確認する。
4. 関連テストと`git diff --check`を実行する。
5. 対象branchを明示してpushする。Public remoteに対する`git push --all`は避ける。

## 推奨フロー

```text
git switch develop
git switch -c feature/example
# 実装 + test
git push -u origin feature/example
# review後developへmerge
# release review後mainへmerge
```

Public `origin`には`main`、`develop`、および公開安全性を満たす`feature/*`を置けます。公開されたら困る内容は、このrepositoryのPublic branch graphのどこにも置きません。
