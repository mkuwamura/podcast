#!/bin/bash
# ==============================================================================
# podcast 自動パブリッシュスクリプト (Linuxサーバー用)
# episodes/ フォルダに音声が追加されたら、自動でコミット＆プッシュして
# GitHub Actions (ポッドキャスト配信パイプライン) をトリガーします。
# ==============================================================================

set -e

# スクリプト自身のディレクトリ（リポジトリルート）に移動
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

echo "=== Podcast Auto Publisher ==="
echo "Working directory: $REPO_DIR"

# 最新のリモート変更を取得
git fetch origin main || true

# 変更があるか確認（未追跡ファイル含む）
if [ -z "$(git status --porcelain)" ]; then
    echo "No new episodes or changes detected. Nothing to push."
    exit 0
fi

echo "Changes detected! Staging and committing..."

# 変更をすべてステージング
git add .

# コミットメッセージの作成（最新の音声ファイル名を含める）
LATEST_AUDIO=$(git status --porcelain | grep -E '\.(m4a|mp3|wav)$' | head -n 1 | awk '{print $2}' || true)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

if [ -n "$LATEST_AUDIO" ]; then
    COMMIT_MSG="Publish new episode: $(basename "$LATEST_AUDIO") ($TIMESTAMP)"
else
    COMMIT_MSG="Update podcast content: $TIMESTAMP"
fi

git commit -m "$COMMIT_MSG"

echo "Pushing to GitHub (origin/main)..."
git push origin main

echo "Successfully pushed! GitHub Actions will build and deploy the podcast feed."
