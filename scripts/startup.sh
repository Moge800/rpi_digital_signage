#!/bin/bash
# Digital Signage Startup Script for Production
# This script starts the signage application in kiosk mode

set -e  # エラーで停止

# --------------------------
#  設定
# --------------------------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${PROJECT_DIR}/logs"
STARTUP_LOG="${LOG_DIR}/startup.log"

# --------------------------
#  ログディレクトリ作成
# --------------------------
mkdir -p "${LOG_DIR}"

# --------------------------
#  ログ出力関数
# --------------------------
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "${STARTUP_LOG}"
}

# --------------------------
#  エラーハンドラ
# --------------------------
error_exit() {
    log "ERROR: $1"
    exit 1
}

# --------------------------
#  起動処理
# --------------------------
log "========================================="
log "Starting Digital Signage System"
log "========================================="
log "Project directory: ${PROJECT_DIR}"

# プロジェクトディレクトリに移動
cd "${PROJECT_DIR}" || error_exit "Failed to change directory to ${PROJECT_DIR}"

# .envファイルの存在確認
if [ ! -f ".env" ]; then
    error_exit ".env file not found. Please create it from .env.example"
fi

# uv が利用可能か確認
if ! command -v uv &> /dev/null; then
    error_exit "uv is not installed. Please install uv first."
fi

# 仮想環境の確認・セットアップ
log "Checking Python virtual environment..."
if [ ! -d ".venv" ]; then
    log "Virtual environment not found. Creating..."
    uv venv || error_exit "Failed to create virtual environment"
fi

# 依存関係のインストール
log "Installing dependencies..."
uv sync || error_exit "Failed to install dependencies"

# Kioskモードを有効化（.envを書き換え）
log "Enabling Kiosk mode..."
if grep -q "^KIOSK_MODE=" .env; then
    sed -i 's/^KIOSK_MODE=.*/KIOSK_MODE=true/' .env
else
    echo "KIOSK_MODE=true" >> .env
fi

# ディスプレイの電源管理を無効化（スリープ防止）
log "Disabling display power management..."
if command -v xset &> /dev/null; then
    export DISPLAY=:0
    xset s off         # スクリーンセーバー無効
    xset -dpms         # DPMS無効（ディスプレイの電源管理）
    xset s noblank     # ブランク無効
    log "Display power management disabled"
else
    log "WARNING: xset not found. Display power management not disabled."
fi

# カーソルを非表示にする（unclutter使用）
log "Hiding mouse cursor..."
if command -v unclutter &> /dev/null; then
    unclutter -idle 0.1 -root &
    log "Mouse cursor hidden"
else
    log "WARNING: unclutter not found. Mouse cursor will be visible."
    log "Install with: sudo apt install unclutter"
fi

# アプリケーション起動
log "Starting application..."
uv run python main.py 2>&1 | tee -a "${LOG_DIR}/app.log"

# 終了処理
log "Application stopped"
log "========================================="
