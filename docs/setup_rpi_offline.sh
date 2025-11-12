#!/bin/bash
# オフライン環境用セットアップスクリプト
# 事前に packages/ ディレクトリに依存パッケージが必要

set -e

echo "======================================"
echo "  Offline Setup for Raspberry Pi 5"
echo "======================================"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# パッケージディレクトリの確認
if [ ! -d "packages" ]; then
    echo -e "${RED}エラー: packages/ ディレクトリが見つかりません${NC}"
    echo -e "${YELLOW}開発PCで以下を実行してパッケージをダウンロードしてください:${NC}"
    echo -e "  uv pip download -r pyproject.toml --platform linux --dest packages/"
    exit 1
fi

# 1. 仮想環境の作成
echo -e "${GREEN}[1/5] 仮想環境を作成中...${NC}"
python3 -m venv .venv
source .venv/bin/activate

# 2. パッケージのインストール (オフライン)
echo -e "${GREEN}[2/5] パッケージをインストール中...${NC}"
pip install --no-index --find-links=packages plotly pydantic-settings pymcprotocol python-dotenv streamlit streamlit-autorefresh

# 3. .envファイルの作成
echo -e "${GREEN}[3/5] 環境変数ファイルをセットアップ中...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠️  .envファイルを編集してPLC接続情報を設定してください${NC}"
    echo -e "${YELLOW}   nano .env${NC}"
fi

# 4. ログディレクトリの作成
echo -e "${GREEN}[4/5] ログディレクトリを作成中...${NC}"
mkdir -p logs

# 5. systemdサービスファイルの作成
echo -e "${GREEN}[5/5] systemdサービスを設定中...${NC}"
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
fi

# Streamlit設定
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
echo -e "  オフラインセットアップ完了！"
echo -e "======================================${NC}"
echo ""
echo -e "${YELLOW}次のステップ:${NC}"
echo -e "1. .envファイルを編集"
echo -e "   ${GREEN}nano .env${NC}"
echo -e ""
echo -e "2. 動作確認"
echo -e "   ${GREEN}python main.py${NC}"
echo -e ""
echo -e "3. 自動起動を有効化"
echo -e "   ${GREEN}sudo systemctl enable digital-signage.service${NC}"
echo -e "   ${GREEN}sudo systemctl start digital-signage.service${NC}"
