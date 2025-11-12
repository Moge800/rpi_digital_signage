#!/bin/bash
# Raspberry Pi 5 自動セットアップスクリプト

set -e

echo "======================================"
echo "  Digital Signage Setup for RPi 5"
echo "======================================"

# 色の定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. システムパッケージの更新
echo -e "${GREEN}[1/7] システムパッケージを更新中...${NC}"
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git curl

# 2. uvのインストール確認
echo -e "${GREEN}[2/7] uvをインストール中...${NC}"
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
else
    echo -e "${YELLOW}uvは既にインストール済みです${NC}"
fi

# 3. 仮想環境のセットアップ
echo -e "${GREEN}[3/7] 仮想環境をセットアップ中...${NC}"
uv sync

# 4. .envファイルの作成
echo -e "${GREEN}[4/7] 環境変数ファイルをセットアップ中...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠️  .envファイルを編集してPLC接続情報を設定してください${NC}"
    echo -e "${YELLOW}   nano .env${NC}"
else
    echo -e "${YELLOW}.envファイルは既に存在します${NC}"
fi

# 5. ログディレクトリの作成
echo -e "${GREEN}[5/7] ログディレクトリを作成中...${NC}"
mkdir -p logs

# 6. systemdサービスファイルの作成
echo -e "${GREEN}[6/7] systemdサービスを設定中...${NC}"
SERVICE_FILE="/etc/systemd/system/digital-signage.service"
if [ ! -f "$SERVICE_FILE" ]; then
    sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Digital Signage System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$(pwd)/.venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl daemon-reload
    echo -e "${YELLOW}サービスを有効化するには: sudo systemctl enable digital-signage.service${NC}"
    echo -e "${YELLOW}サービスを起動するには: sudo systemctl start digital-signage.service${NC}"
else
    echo -e "${YELLOW}サービスファイルは既に存在します${NC}"
fi

# 7. Streamlit設定
echo -e "${GREEN}[7/7] Streamlit設定を作成中...${NC}"
mkdir -p ~/.streamlit
if [ ! -f ~/.streamlit/config.toml ]; then
    cat > ~/.streamlit/config.toml <<EOF
[server]
headless = true
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false
EOF
fi

echo -e "${GREEN}======================================"
echo -e "  セットアップ完了！"
echo -e "======================================${NC}"
echo ""
echo -e "${YELLOW}次のステップ:${NC}"
echo -e "1. .envファイルを編集してPLC情報を設定"
echo -e "   ${GREEN}nano .env${NC}"
echo -e ""
echo -e "2. アプリケーションを起動"
echo -e "   ${GREEN}python main.py${NC}"
echo -e ""
echo -e "3. (オプション) 自動起動を設定"
echo -e "   ${GREEN}sudo systemctl enable digital-signage.service${NC}"
echo -e "   ${GREEN}sudo systemctl start digital-signage.service${NC}"
echo -e ""
echo -e "4. ブラウザで確認"
echo -e "   ${GREEN}http://localhost:8501${NC}"
