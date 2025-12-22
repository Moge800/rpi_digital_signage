#!/bin/bash
# Raspberry Pi デジタルサイネージ起動スクリプト (オフライン対応)
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
    echo -e "${YELLOW}オフラインインストール手順:${NC}"
    echo "  1. scripts/download_python_packages_windows.ps1 を実行 (Windows/WSL環境)"
    echo "  2. python_packages.tar.gz をUSBメモリで転送"
    echo "  3. tar -xzf python_packages.tar.gz"
    echo "  4. cd python_packages && sudo ./install_python.sh"
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
echo -e "  Python: $(python --version)"

# オフライン環境対応: uvとpyproject.tomlの依存関係を手動インストール
echo ""
echo -e "${YELLOW}[3/3] 依存関係確認 (オフライン対応)${NC}"

# uvが既にインストールされているか確認
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}警告: uvが見つかりません${NC}"
    echo -e "${YELLOW}オンライン環境で以下を実行してください:${NC}"
    echo "  pip install uv"
    echo "  uv sync"
    echo ""
    echo -e "${YELLOW}オフライン環境では pip install を使用します${NC}"
    
    # pyproject.tomlから依存パッケージを手動インストール
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        echo -e "${RED}requirements.txtが見つかりません${NC}"
        echo -e "${YELLOW}オンライン環境で以下を実行してください:${NC}"
        echo "  uv pip compile pyproject.toml -o requirements.txt"
    fi
else
    echo -e "${GREEN}✓ uv $(uv --version)${NC}"
    echo -e "${YELLOW}依存関係を同期します...${NC}"
    uv sync
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}アプリケーション起動${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# main.py実行
python main.py

