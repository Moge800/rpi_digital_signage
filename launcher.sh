#!/bin/bash
# Raspberry Pi デジタルサイネージ起動スクリプト (FastAPI + Streamlit 2プロセス構成)
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
echo -e "${GREEN}(FastAPI + Streamlit 構成)${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# プロジェクトルートに移動
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 設定読み込み
API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
STREAMLIT_PORT="${STREAMLIT_PORT:-8501}"

# PIDファイル
API_PID_FILE="/tmp/signage_api.pid"
STREAMLIT_PID_FILE="/tmp/signage_streamlit.pid"

# 初期化フラグをクリア（再起動時に初期化を実行するため）
rm -f /tmp/signage_initialized.flag
rm -f /tmp/signage_frontend_initialized.flag

# クリーンアップ関数
cleanup() {
    echo ""
    echo -e "${YELLOW}シャットダウン中...${NC}"
    
    # Streamlit停止
    if [ -f "$STREAMLIT_PID_FILE" ]; then
        STREAMLIT_PID=$(cat "$STREAMLIT_PID_FILE")
        if kill -0 "$STREAMLIT_PID" 2>/dev/null; then
            echo -e "${YELLOW}Streamlit (PID: $STREAMLIT_PID) を停止中...${NC}"
            kill "$STREAMLIT_PID" 2>/dev/null || true
        fi
        rm -f "$STREAMLIT_PID_FILE"
    fi
    
    # API停止（シャットダウンエンドポイント経由で安全に停止）
    if [ -f "$API_PID_FILE" ]; then
        API_PID=$(cat "$API_PID_FILE")
        if kill -0 "$API_PID" 2>/dev/null; then
            echo -e "${YELLOW}APIサーバー (PID: $API_PID) を停止中...${NC}"
            # まずAPIのシャットダウンエンドポイントを呼ぶ（PLCを安全に切断）
            curl -s -X POST "http://${API_HOST}:${API_PORT}/api/shutdown" > /dev/null 2>&1 || true
            sleep 1
            # まだ生きていたらkill
            kill "$API_PID" 2>/dev/null || true
        fi
        rm -f "$API_PID_FILE"
    fi
    
    echo -e "${GREEN}シャットダウン完了${NC}"
    exit 0
}

# シグナルハンドラ登録
trap cleanup SIGINT SIGTERM

echo -e "${YELLOW}[1/4] 環境確認${NC}"

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
echo -e "${YELLOW}[2/4] 仮想環境確認${NC}"

# 仮想環境作成・アクティベート
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}仮想環境を作成します...${NC}"
    $PYTHON_CMD -m venv .venv
fi

source .venv/bin/activate

echo -e "${GREEN}✓ 仮想環境アクティベート完了${NC}"

echo ""
echo -e "${YELLOW}[3/4] 依存関係確認${NC}"

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
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}[4/4] アプリケーション起動${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# APIサーバー起動 (バックグラウンド)
echo -e "${YELLOW}APIサーバーを起動中... (${API_HOST}:${API_PORT})${NC}"
uv run uvicorn src.api.main:app --host "$API_HOST" --port "$API_PORT" &
API_PID=$!
echo $API_PID > "$API_PID_FILE"
echo -e "${GREEN}✓ APIサーバー起動 (PID: $API_PID)${NC}"

# APIサーバーの起動を待つ
echo -e "${YELLOW}APIサーバーの起動を待機中...${NC}"
for i in {1..30}; do
    if curl -s "http://${API_HOST}:${API_PORT}/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ APIサーバー正常起動${NC}"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo -e "${RED}エラー: APIサーバーの起動がタイムアウトしました${NC}"
        cleanup
        exit 1
    fi
done

echo ""

# Streamlit起動 (バックグラウンド)
echo -e "${YELLOW}Streamlitを起動中... (port ${STREAMLIT_PORT})${NC}"
uv run streamlit run src/frontend/signage_app.py \
    --server.port "$STREAMLIT_PORT" \
    --server.headless true \
    --server.address 0.0.0.0 &
STREAMLIT_PID=$!
echo $STREAMLIT_PID > "$STREAMLIT_PID_FILE"
echo -e "${GREEN}✓ Streamlit起動 (PID: $STREAMLIT_PID)${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}起動完了!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "  API:       http://${API_HOST}:${API_PORT}"
echo -e "  Frontend:  http://localhost:${STREAMLIT_PORT}"
echo ""
echo -e "${YELLOW}Ctrl+C で終了${NC}"
echo ""

# プロセスを監視
wait $API_PID $STREAMLIT_PID
