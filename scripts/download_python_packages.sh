#!/bin/bash
# Raspberry Pi用Pythonパッケージダウンロードスクリプト
# ⚠️ 警告: このスクリプトはRaspberry Pi実機での実行を推奨します
#
# 理由: WSL/Ubuntu (x86_64) でダウンロードしたパッケージは
#       Raspberry Pi (ARM64) では動作しません
#
# 使い方 (推奨: Raspberry Pi実機で実行):
#   1. ネット接続可能なRaspberry Piでこのスクリプトを実行
#   2. ./download_python_packages.sh
#   3. 生成されたpython_packages.tar.gzをオフライン環境に転送
#
# 代替方法 (WSL/Ubuntu環境でARM64パッケージ取得):
#   環境変数FORCE_ARM64=1を設定して実行
#   FORCE_ARM64=1 ./download_python_packages.sh
#   ※ただし依存関係の解決が不完全な可能性あり

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

# アーキテクチャ検出
CURRENT_ARCH=$(dpkg --print-architecture)
TARGET_ARCH="arm64"  # Raspberry Pi 5はARM64

echo -e "${YELLOW}現在のアーキテクチャ: ${CURRENT_ARCH}${NC}"
echo -e "${YELLOW}ターゲットアーキテクチャ: ${TARGET_ARCH}${NC}"
echo ""

# アーキテクチャ不一致の警告
if [ "$CURRENT_ARCH" != "$TARGET_ARCH" ] && [ -z "$FORCE_ARM64" ]; then
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}⚠️ 警告: アーキテクチャ不一致${NC}"
    echo -e "${RED}========================================${NC}"
    echo -e "${YELLOW}現在の環境: ${CURRENT_ARCH}${NC}"
    echo -e "${YELLOW}Raspberry Pi 5: arm64 (aarch64)${NC}"
    echo ""
    echo -e "${RED}このままダウンロードしたパッケージはRaspberry Piで動作しません！${NC}"
    echo ""
    echo -e "${GREEN}推奨方法:${NC}"
    echo "  1. このスクリプトをRaspberry Pi実機で実行"
    echo "  2. ネット接続可能なRaspberry Piでパッケージ取得"
    echo "  3. tar.gzファイルをオフライン環境に転送"
    echo ""
    echo -e "${YELLOW}それでも続行する場合 (非推奨):${NC}"
    echo "  FORCE_ARM64=1 ./download_python_packages.sh"
    echo ""
    exit 1
fi

# ARM64パッケージ取得の準備
if [ "$CURRENT_ARCH" != "$TARGET_ARCH" ] && [ -n "$FORCE_ARM64" ]; then
    echo -e "${YELLOW}FORCE_ARM64モード: ARM64パッケージを取得します${NC}"
    echo -e "${YELLOW}警告: 依存関係の解決が不完全な可能性があります${NC}"
    echo ""
    
    # arm64アーキテクチャを有効化
    if ! dpkg --print-foreign-architectures | grep -q arm64; then
        echo -e "${YELLOW}arm64アーキテクチャを追加中...${NC}"
        sudo dpkg --add-architecture arm64 || {
            echo -e "${RED}arm64アーキテクチャの追加に失敗しました${NC}"
            exit 1
        }
        sudo apt-get update
    fi
    
    APT_ARCH_FLAG=":arm64"
else
    APT_ARCH_FLAG=""
fi

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
echo -e "${YELLOW}Downloading python3${APT_ARCH_FLAG} (3.11+)...${NC}"
apt-get download python3${APT_ARCH_FLAG} python3-venv${APT_ARCH_FLAG} python3-dev${APT_ARCH_FLAG} 2>/dev/null || {
    echo -e "${RED}⚠ python3パッケージがリポジトリに見つかりません${NC}"
    echo -e "${YELLOW}apt-get update を先に実行してください${NC}"
    exit 1
}

# システムpip (念のため)
echo -e "${YELLOW}Downloading python3-pip${APT_ARCH_FLAG}...${NC}"
apt-get download python3-pip${APT_ARCH_FLAG}

# ビルドツール (ARM64環境の場合のみ)
if [ -z "$APT_ARCH_FLAG" ]; then
    echo -e "${YELLOW}Downloading build-essential...${NC}"
    apt-get download build-essential gcc g++ make libc6-dev
else
    echo -e "${YELLOW}Skipping build-essential (クロスコンパイル非対応)${NC}"
fi

# 依存ライブラリ
echo -e "${YELLOW}Downloading development libraries${APT_ARCH_FLAG}...${NC}"
apt-get download libffi-dev${APT_ARCH_FLAG} libssl-dev${APT_ARCH_FLAG} zlib1g-dev${APT_ARCH_FLAG} libbz2-dev${APT_ARCH_FLAG} \
    libreadline-dev${APT_ARCH_FLAG} libsqlite3-dev${APT_ARCH_FLAG} libncurses5-dev${APT_ARCH_FLAG} libncursesw5-dev${APT_ARCH_FLAG} \
    xz-utils${APT_ARCH_FLAG} tk-dev${APT_ARCH_FLAG} libxml2-dev${APT_ARCH_FLAG} libxmlsec1-dev${APT_ARCH_FLAG} liblzma-dev${APT_ARCH_FLAG} 2>/dev/null || true

# 依存関係を自動解決してダウンロード
if [ -z "$APT_ARCH_FLAG" ]; then
    echo -e "${YELLOW}Downloading dependencies...${NC}"
    apt-get download $(apt-cache depends python3 python3-venv python3-dev build-essential \
        | grep -E 'Depends|PreDepends' \
        | awk '{print $2}' \
        | grep -v '<' \
        | sort -u) 2>/dev/null || true
else
    echo -e "${YELLOW}Skipping automatic dependency resolution (クロスアーキテクチャ)${NC}"
fi

cd ../..

echo ""
echo -e "${GREEN}[3/4] インストールスクリプト生成${NC}"

# インストールスクリプトを生成
cat > "${OUTPUT_DIR}/install_python.sh" << 'INSTALL_SCRIPT'
#!/bin/bash
# Raspberry Pi上で実行: Pythonインストールスクリプト
# オフライン環境対応 (Python 3.11+ Bookworm標準)

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Python オフラインインストール${NC}"
echo -e "${GREEN}Raspberry Pi OS Bookworm (Python 3.11+)${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 権限チェック
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}このスクリプトはroot権限で実行してください${NC}"
    echo "実行例: sudo ./install_python.sh"
    exit 1
fi

# カレントディレクトリ確認
if [ ! -d "debs" ]; then
    echo -e "${RED}debsディレクトリが見つかりません${NC}"
    echo "このスクリプトはpython_packages/ディレクトリ内で実行してください"
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
echo -e "${GREEN}[2/3] Pythonインストール確認${NC}"

# Python 3.11以上を確認 (Bookworm標準)
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
    PYTHON_VERSION=$(python3.11 --version)
    echo -e "${GREEN}✓ ${PYTHON_VERSION} インストール成功${NC}"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓ ${PYTHON_VERSION} インストール成功${NC}"
else
    echo -e "${RED}✗ python3コマンドが見つかりません${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}[3/3] 仮想環境テスト${NC}"

# テスト用仮想環境作成
TEST_VENV="/tmp/test_venv_rpi"
rm -rf "$TEST_VENV"

$PYTHON_CMD -m venv "$TEST_VENV"
source "$TEST_VENV/bin/activate"

echo -e "${GREEN}仮想環境Python: $(python --version)${NC}"
echo -e "${GREEN}仮想環境pip: $(pip --version)${NC}"

deactivate
rm -rf "$TEST_VENV"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Pythonインストール完了${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "次のステップ:"
echo "  1. プロジェクトディレクトリに移動"
echo "  2. $PYTHON_CMD -m venv .venv"
echo "  3. source .venv/bin/activate"
echo "  4. pip install uv"
echo "  5. uv sync"
echo ""
echo "インストールログ: $(pwd)/install.log"
INSTALL_SCRIPT

chmod +x "${OUTPUT_DIR}/install_python.sh"

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
echo -e "${YELLOW}オフライン環境への転送手順:${NC}"
echo "  1. USBメモリに ${ARCHIVE_NAME} をコピー"
echo "  2. オフライン環境のRaspberry Piで展開:"
echo "     tar -xzf ${ARCHIVE_NAME}"
echo "  3. インストール:"
echo "     cd ${OUTPUT_DIR}"
echo "     sudo ./install_python.sh"
echo ""
echo -e "${YELLOW}重要: ${NC}"
echo "  このパッケージはRaspberry Pi (ARM64)専用です"
echo "  x86_64環境では動作しません"
echo ""
echo -e "${GREEN}パッケージ総容量: $(du -sh ${OUTPUT_DIR} | cut -f1)${NC}"
echo -e "${GREEN}アーカイブサイズ: $(du -sh ${ARCHIVE_NAME} | cut -f1)${NC}"
