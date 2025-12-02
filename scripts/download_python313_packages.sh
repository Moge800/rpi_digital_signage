#!/bin/bash
# Raspberry Pi用Pythonパッケージダウンロードスクリプト
# Ubuntu/Debian/WSL環境で実行してください
#
# 使い方:
#   1. WSLまたはLinux環境でこのスクリプトを実行
#   2. ./download_python_packages.sh
#   3. 生成されたpython_packages/フォルダをUSBメモリ等でラズパイに転送

set -e  # エラーで即座に終了

# 色付き出力
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Pythonパッケージダウンローダー${NC}"
echo -e "${GREEN}Raspberry Pi OS (Debian 12 Bookworm)用${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 出力ディレクトリ
OUTPUT_DIR="python_packages"
DEB_DIR="${OUTPUT_DIR}/debs"
ARCHIVE_NAME="python_packages.tar.gz"

# ディレクトリ初期化
if [ -d "$OUTPUT_DIR" ]; then
    echo -e "${YELLOW}既存の${OUTPUT_DIR}を削除します...${NC}"
    rm -rf "$OUTPUT_DIR"
fi

mkdir -p "$DEB_DIR"

echo -e "${GREEN}[1/4] パッケージリスト更新${NC}"
sudo apt-get update

echo ""
echo -e "${GREEN}[2/4] Python関連パッケージをダウンロード${NC}"
echo "以下のパッケージをダウンロードします:"
echo "  - python3 (標準パッケージ, 3.11+)"
echo "  - python3-venv"
echo "  - python3-dev"
echo "  - python3-pip (システムpip、念のため)"
echo "  - build-essential (コンパイル環境)"
echo "  - libffi-dev, libssl-dev (依存ライブラリ)"
echo ""

# 依存関係も含めてダウンロード
cd "$DEB_DIR"

# Python 3.11本体 + venv + dev (Bookworm標準)
echo -e "${YELLOW}Downloading python3 (3.11+)...${NC}"
apt-get download python3 python3-venv python3-dev 2>/dev/null || {
    echo -e "${RED}⚠ python3パッケージがリポジトリに見つかりません${NC}"
    echo -e "${YELLOW}apt-get update を先に実行してください${NC}"
    exit 1
}

# システムpip (念のため)
echo -e "${YELLOW}Downloading python3-pip...${NC}"
apt-get download python3-pip

# ビルドツール
echo -e "${YELLOW}Downloading build-essential...${NC}"
apt-get download build-essential gcc g++ make libc6-dev

# 依存ライブラリ
echo -e "${YELLOW}Downloading development libraries...${NC}"
apt-get download libffi-dev libssl-dev zlib1g-dev libbz2-dev \
    libreadline-dev libsqlite3-dev libncurses5-dev libncursesw5-dev \
    xz-utils tk-dev libxml2-dev libxmlsec1-dev liblzma-dev

# 依存関係を自動解決してダウンロード
echo -e "${YELLOW}Downloading dependencies...${NC}"
apt-get download $(apt-cache depends python3.13 python3.13-venv python3.13-dev build-essential \
    | grep -E 'Depends|PreDepends' \
    | awk '{print $2}' \
    | grep -v '<' \
    | sort -u) 2>/dev/null || true

cd ../..

echo ""
echo -e "${GREEN}[3/4] インストールスクリプト生成${NC}"

# インストールスクリプトを生成
cat > "${OUTPUT_DIR}/install_python313.sh" << 'INSTALL_SCRIPT'
#!/bin/bash
# Raspberry Pi上で実行: Python 3.13インストールスクリプト
# オフライン環境対応

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Python 3.13 オフラインインストール${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 権限チェック
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}このスクリプトはroot権限で実行してください${NC}"
    echo "実行例: sudo ./install_python313.sh"
    exit 1
fi

# カレントディレクトリ確認
if [ ! -d "debs" ]; then
    echo -e "${RED}debsディレクトリが見つかりません${NC}"
    echo "このスクリプトはpython313_packages/ディレクトリ内で実行してください"
    exit 1
fi

echo -e "${GREEN}[1/3] .debパッケージをインストール${NC}"
echo "パッケージ数: $(ls debs/*.deb 2>/dev/null | wc -l)"
echo ""

cd debs

# すべての.debファイルをインストール
# --force-depends: 依存関係エラーを無視 (オフライン環境用)
echo -e "${YELLOW}dpkgでインストール開始...${NC}"
dpkg -i *.deb 2>&1 | tee ../install.log || {
    echo -e "${YELLOW}依存関係エラーが発生しました。修復を試みます...${NC}"
    apt-get install -f -y || echo -e "${RED}修復失敗。手動確認が必要です${NC}"
}

cd ..

echo ""
echo -e "${GREEN}[2/3] Python 3.13インストール確認${NC}"

if command -v python3.13 &> /dev/null; then
    PYTHON_VERSION=$(python3.13 --version)
    echo -e "${GREEN}✓ ${PYTHON_VERSION} インストール成功${NC}"
else
    echo -e "${RED}✗ python3.13コマンドが見つかりません${NC}"
    echo -e "${YELLOW}python3.11等の代替バージョンを確認してください${NC}"
    python3 --version || echo "python3コマンドも見つかりません"
    exit 1
fi

echo ""
echo -e "${GREEN}[3/3] 仮想環境テスト${NC}"

# テスト用仮想環境作成
TEST_VENV="/tmp/test_venv313"
rm -rf "$TEST_VENV"

python3.13 -m venv "$TEST_VENV"
source "$TEST_VENV/bin/activate"

echo -e "${GREEN}仮想環境Python: $(python --version)${NC}"
echo -e "${GREEN}仮想環境pip: $(pip --version)${NC}"

deactivate
rm -rf "$TEST_VENV"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Python 3.13インストール完了${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "次のステップ:"
echo "  1. プロジェクトディレクトリに移動"
echo "  2. python3.13 -m venv .venv"
echo "  3. source .venv/bin/activate"
echo "  4. pip install uv"
echo "  5. uv sync"
echo ""
echo "インストールログ: $(pwd)/install.log"
INSTALL_SCRIPT

chmod +x "${OUTPUT_DIR}/install_python313.sh"

echo ""
echo -e "${GREEN}[4/4] アーカイブ作成${NC}"

tar -czf "$ARCHIVE_NAME" "$OUTPUT_DIR"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ ダウンロード完了${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}生成されたファイル:${NC}"
echo "  1. ${OUTPUT_DIR}/          - パッケージディレクトリ"
echo "  2. ${ARCHIVE_NAME}         - 圧縮アーカイブ (転送用)"
echo ""
echo -e "${YELLOW}Raspberry Piへの転送手順:${NC}"
echo "  1. USBメモリに ${ARCHIVE_NAME} をコピー"
echo "  2. Raspberry Piで展開:"
echo "     tar -xzf ${ARCHIVE_NAME}"
echo "  3. インストール:"
echo "     cd ${OUTPUT_DIR}"
echo "     sudo ./install_python313.sh"
echo ""
echo -e "${GREEN}パッケージ総容量: $(du -sh ${OUTPUT_DIR} | cut -f1)${NC}"
echo -e "${GREEN}アーカイブサイズ: $(du -sh ${ARCHIVE_NAME} | cut -f1)${NC}"
