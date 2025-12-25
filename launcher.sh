#!/bin/bash
# Raspberry Pi デジタルサイネージ起動スクリプト
# 
# main.py を通じて FastAPI + Streamlit + Kioskブラウザを起動します。
# 
# 使い方:
#   chmod +x launcher.sh
#   ./launcher.sh

set -e  # エラー時に即座に終了

# 色付き出力
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Raspberry Pi デジタルサイネージ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# プロジェクトルートに移動
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${YELLOW}[1/3] 環境確認${NC}"

# Python 3.11確認 (またはpython3)
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo -e "${RED}エラー: python3コマンドが見つかりません${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version)
echo -e "${GREEN}✓ ${PYTHON_VERSION}${NC}"

# .envファイル確認
if [ ! -f ".env" ]; then
    echo -e "${RED}エラー: .envファイルが見つかりません${NC}"
    echo -e "${YELLOW}セットアップ方法:${NC}"
    echo "  cp .env.example .env"
    echo "  nano .env  # 設定を編集"
    exit 1
fi

echo -e "${GREEN}✓ .envファイル確認${NC}"

echo ""
echo -e "${YELLOW}[2/3] 仮想環境確認${NC}"

# 仮想環境作成・アクティベート
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}仮想環境を作成します...${NC}"
    $PYTHON_CMD -m venv .venv
fi

source .venv/bin/activate

echo -e "${GREEN}✓ 仮想環境アクティベート完了${NC}"

# uvが既にインストールされているか確認
if command -v uv &> /dev/null; then
    echo -e "${GREEN}✓ uv $(uv --version)${NC}"
    echo -e "${YELLOW}依存関係を同期します...${NC}"
    uv sync
else
    echo -e "${YELLOW}pip install を使用します${NC}"
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    fi
fi

echo ""
echo -e "${YELLOW}[3/3] アプリケーション起動${NC}"
echo ""

# --watchdog オプションでWatchdogモード（API監視付き）起動
# 通常モード（APIを直接管理）: --watchdog なし
WATCHDOG_MODE="${1:-}"

if [ "$WATCHDOG_MODE" = "--watchdog" ]; then
    echo -e "${GREEN}Watchdogモードで起動します (API監視付き)${NC}"
    if command -v uv &> /dev/null; then
        uv run python main.py --watchdog
    else
        python main.py --watchdog
    fi
else
    echo -e "${GREEN}通常モードで起動します${NC}"
    # main.py を実行 (Pythonランチャーに処理を委譲)
    if command -v uv &> /dev/null; then
        uv run python main.py
    else
        python main.py
    fi
fi
