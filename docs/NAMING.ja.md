# Fossight 命名記録

[English](NAMING.md) | **日本語**

## 正式名称と読み

- 製品名: **Fossight**
- 正式なカタカナ読み: **フォサイト**

## 名称の由来

**Fossight** は **FOSS + Sight** を組み合わせた造語です。

- **FOSS**: Free and Open Source Software。ローカル環境で実際に利用しているOSSを管理・監視するツールであることを示します。
- **Sight**: 見る、見渡す、視野に入れておく、という意味です。各OSSが何をするものか把握し、Local / Upstream の状態を俯瞰し、変化を監視する役割を表します。

さらに、英語の **Foresight（先を見通す、先見）** に近い響きを意図的に重ねています。Upstreamの変化やローカルとの差分を早めに把握し、見落とされた保守負債になる前に気付ける、というFossightの役割にも合致します。

日本語では **「フォサイト」** を正式な読みとします。UI、ドキュメント見出し、Modora上の表示名は **Fossight** に統一します。

## 旧名称と互換性

旧製品名は **OSS Update Watch** です。製品・ブランド表示は **Fossight** に変更しましたが、既存スクリプトや状態保存先、Modora登録を壊さないため、当面は以下の内部識別子を維持します。

- `oss-update-watch`（package / Modora module ID等）
- `oss_update_watch`（Python module）
- `oss-update-watch-desktop.exe`（desktop executable）

これらはユーザー向け製品名ではなく、互換性維持のための内部識別子です。
