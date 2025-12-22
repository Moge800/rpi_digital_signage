#!/bin/bash
# =============================================================================
# マウスカーソル非表示スクリプト
# Raspberry Pi デジタルサイネージ用
# 
# 問題: 画面中央にカーソルが居座って邪魔
# 解決: unclutterでカーソルを自動的に透明化
# =============================================================================

set -e

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "マウスカーソル非表示設定スクリプト"
echo "========================================"
echo ""

# =============================================================================
# unclutter インストール
# =============================================================================
echo -e "${YELLOW}[1/3] unclutter のインストール確認中...${NC}"

if command -v unclutter &> /dev/null; then
    echo -e "${GREEN}  ✓ unclutter は既にインストール済み${NC}"
else
    echo "  unclutter をインストール中..."
    sudo apt update
    sudo apt install -y unclutter
    echo -e "${GREEN}  ✓ unclutter インストール完了${NC}"
fi

# =============================================================================
# 自動起動設定 (autostart)
# =============================================================================
echo -e "${YELLOW}[2/3] 自動起動設定を作成中...${NC}"

AUTOSTART_DIR="$HOME/.config/autostart"
AUTOSTART_FILE="$AUTOSTART_DIR/unclutter.desktop"

mkdir -p "$AUTOSTART_DIR"

cat > "$AUTOSTART_FILE" << 'EOF'
[Desktop Entry]
Type=Application
Name=Unclutter
Comment=Hide mouse cursor when idle
Exec=unclutter -idle 0.1 -root
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF

echo -e "${GREEN}  ✓ 自動起動設定作成: $AUTOSTART_FILE${NC}"

# =============================================================================
# systemdサービス作成（デスクトップ環境なしの場合用）
# =============================================================================
echo -e "${YELLOW}[3/3] systemdサービスを作成中...${NC}"

SERVICE_FILE="/etc/systemd/system/hide-cursor.service"

sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=Hide Mouse Cursor for Digital Signage
After=graphical.target

[Service]
Type=simple
Environment=DISPLAY=:0
ExecStart=/usr/bin/unclutter -idle 0.1 -root
Restart=always
RestartSec=5
User=$USER

[Install]
WantedBy=graphical.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable hide-cursor.service
echo -e "${GREEN}  ✓ systemdサービス作成・有効化完了${NC}"

# =============================================================================
# 今すぐ実行
# =============================================================================
echo ""
echo -e "${YELLOW}unclutter を今すぐ起動中...${NC}"

# 既存のunclutterを停止
pkill unclutter 2>/dev/null || true

# 起動（バックグラウンド）
if [ -n "$DISPLAY" ]; then
    unclutter -idle 0.1 -root &
    echo -e "${GREEN}✓ unclutter 起動完了（カーソルは0.1秒後に非表示）${NC}"
else
    echo -e "${YELLOW}⚠ DISPLAY未設定のため、再起動後に有効になります${NC}"
fi

# =============================================================================
# 完了メッセージ
# =============================================================================
echo ""
echo "========================================"
echo -e "${GREEN}設定完了！${NC}"
echo "========================================"
echo ""
echo "マウスカーソルは以下の状態で非表示になります:"
echo "  • 0.1秒間操作がない場合 → カーソル非表示"
echo "  • マウスを動かす → カーソル再表示"
echo ""
echo "手動で起動/停止する場合:"
echo "  起動: unclutter -idle 0.1 -root &"
echo "  停止: pkill unclutter"
echo ""
echo "サービス管理:"
echo "  状態確認: sudo systemctl status hide-cursor"
echo "  停止:     sudo systemctl stop hide-cursor"
echo "  無効化:   sudo systemctl disable hide-cursor"
