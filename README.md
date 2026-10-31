# Study Podcast Hub

通勤時間（朝60分）を活用して高度情報処理技術者試験（ITサービスマネージャ等）をマスターするためのパーソナル・ポッドキャスト配信リポジトリです。

## 構成

- `shows/itsm/`: ITサービスマネージャ（SM）試験
- `shows/<区分>/`: 将来追加する他試験（PM, SC等）
- `scripts/generate_rss.py`: Apple Podcasts規格準拠のRSSフィード自動生成
- `.github/workflows/deploy.yml`: 音声ファイル追加時に自動でGitHub Pagesへデプロイ

## 使い方

1. NotebookLM等で生成した音声ファイル（`.m4a` または `.mp3`）を `shows/<試験名>/episodes/` に配置する。
2. （任意）チャプターを設定したい場合は、同名の `.txt` ファイルを作成してタイムスタンプを記載する。
3. `git push` すると、GitHub Actionsが自動で `feed.xml` をビルドし、GitHub Pagesに反映されます。
4. iPhoneの公式ポッドキャストアプリで自動ダウンロードされます。
