#!/bin/bash
# =============================================================================
# スクリーンブランク（画面消灯）無効化スクリプト
# Raspberry Pi デジタルサイネージ用
# 
# 問題: キーボード・マウスを抜くと画面が暗くなる
# 原因: systemd-logindがアイドル状態と判断して画面をオフにする
# =============================================================================

set -e

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "スクリーンブランク無効化スクリプト"
echo "========================================"
echo ""

# root権限チェック
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}エラー: このスクリプトはroot権限で実行してください${NC}"
    echo "使用方法: sudo $0"
    exit 1
fi

# =============================================================================
# 対策①: systemd-logind のアイドル判定を無効化
# =============================================================================
echo -e "${YELLOW}[1/3] systemd-logind 設定を更新中...${NC}"

LOGIND_CONF="/etc/systemd/logind.conf"

# バックアップ作成
if [ ! -f "${LOGIND_CONF}.backup" ]; then
    cp "$LOGIND_CONF" "${LOGIND_CONF}.backup"
    echo "  バックアップ作成: ${LOGIND_CONF}.backup"
fi

# IdleAction設定を追加/更新
if grep -q "^IdleAction=" "$LOGIND_CONF"; then
    sed -i 's/^IdleAction=.*/IdleAction=ignore/' "$LOGIND_CONF"
else
    echo "IdleAction=ignore" >> "$LOGIND_CONF"
fi

if grep -q "^IdleActionSec=" "$LOGIND_CONF"; then
    sed -i 's/^IdleActionSec=.*/IdleActionSec=0/' "$LOGIND_CONF"
else
    echo "IdleActionSec=0" >> "$LOGIND_CONF"
fi

echo -e "${GREEN}  ✓ logind.conf 更新完了${NC}"

# =============================================================================
# 対策②: コンソールブランク無効化 (kernel parameter)
# =============================================================================
echo -e "${YELLOW}[2/3] コンソールブランク設定を確認中...${NC}"

CMDLINE="/boot/cmdline.txt"
# Raspberry Pi OS Bookworm以降は/boot/firmware/cmdline.txt
if [ -f "/boot/firmware/cmdline.txt" ]; then
    CMDLINE="/boot/firmware/cmdline.txt"
fi

if [ -f "$CMDLINE" ]; then
    # バックアップ作成
    if [ ! -f "${CMDLINE}.backup" ]; then
        cp "$CMDLINE" "${CMDLINE}.backup"
        echo "  バックアップ作成: ${CMDLINE}.backup"
    fi
    
    # consoleblank=0 が無ければ追加
    if ! grep -q "consoleblank=0" "$CMDLINE"; then
        # 改行なしで追記（cmdline.txtは1行）
        sed -i 's/$/ consoleblank=0/' "$CMDLINE"
        echo -e "${GREEN}  ✓ consoleblank=0 を追加${NC}"
    else
        echo -e "${GREEN}  ✓ consoleblank=0 は既に設定済み${NC}"
    fi
else
    echo -e "${YELLOW}  ⚠ $CMDLINE が見つかりません（スキップ）${NC}"
fi

# =============================================================================
# 対策③: X11スクリーンセーバー無効化（デスクトップ環境使用時）
# =============================================================================
echo -e "${YELLOW}[3/3] X11スクリーンセーバー設定を作成中...${NC}"

XORG_CONF_DIR="/etc/X11/xorg.conf.d"
XORG_CONF="${XORG_CONF_DIR}/10-blanking.conf"

if [ -d "/etc/X11" ]; then
    mkdir -p "$XORG_CONF_DIR"
    
    cat > "$XORG_CONF" << 'EOF'
Section "ServerFlags"
    Option "BlankTime" "0"
    Option "StandbyTime" "0"
    Option "SuspendTime" "0"
    Option "OffTime" "0"
EndSection
EOF
    
    echo -e "${GREEN}  ✓ X11設定ファイル作成: $XORG_CONF${NC}"
else
    echo -e "${YELLOW}  ⚠ X11が見つかりません（スキップ）${NC}"
fi

# =============================================================================
# systemd-logind 再起動
# =============================================================================
echo ""
echo -e "${YELLOW}systemd-logind を再起動中...${NC}"
systemctl restart systemd-logind
echo -e "${GREEN}✓ systemd-logind 再起動完了${NC}"

# =============================================================================
# 完了メッセージ
# =============================================================================
echo ""
echo "========================================"
echo -e "${GREEN}設定完了！${NC}"
echo "========================================"
echo ""
echo "以下の設定が適用されました:"
echo "  • IdleAction=ignore"
echo "  • IdleActionSec=0"
echo "  • consoleblank=0 (要再起動)"
echo "  • X11 BlankTime=0"
echo ""
echo -e "${YELLOW}注意: 一部の設定は再起動後に有効になります${NC}"
echo ""
read -p "今すぐ再起動しますか？ (y/N): " answer
if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
    echo "再起動します..."
    reboot
else
    echo "後で手動で再起動してください: sudo reboot"
fi
