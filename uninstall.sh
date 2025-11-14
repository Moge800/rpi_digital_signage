#!/bin/bash
# Digital Signage Uninstaller
# This script removes the systemd service and optionally cleans up project files

set -e

SERVICE_NAME="digital-signage"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================="
echo "Digital Signage Uninstaller"
echo "========================================="
echo ""

# root権限チェック
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root"
    echo "Please run: sudo $0"
    exit 1
fi

# サービスが存在するか確認
if [ ! -f "${SERVICE_FILE}" ]; then
    echo "Service file not found: ${SERVICE_FILE}"
    echo "Service may not be installed."
else
    echo "Found service: ${SERVICE_NAME}"
    
    # サービス停止
    echo "Stopping service..."
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        systemctl stop "${SERVICE_NAME}"
        echo "Service stopped."
    else
        echo "Service is not running."
    fi
    
    # 自動起動無効化
    echo "Disabling service..."
    if systemctl is-enabled --quiet "${SERVICE_NAME}"; then
        systemctl disable "${SERVICE_NAME}"
        echo "Service disabled."
    else
        echo "Service is not enabled."
    fi
    
    # サービスファイル削除
    echo "Removing service file..."
    rm -f "${SERVICE_FILE}"
    echo "Service file removed."
    
    # systemd再読み込み
    echo "Reloading systemd daemon..."
    systemctl daemon-reload
    systemctl reset-failed
fi

echo ""
echo "========================================="
echo "Service uninstalled successfully!"
echo "========================================="
echo ""

# プロジェクトファイル削除の確認
read -p "Do you want to remove project files? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "WARNING: This will delete the following:"
    echo "  - ${PROJECT_DIR}"
    echo "  - All source code, logs, and configuration files"
    echo ""
    read -p "Are you sure? Type 'yes' to confirm: " CONFIRM
    
    if [ "$CONFIRM" = "yes" ]; then
        echo "Removing project files..."
        cd /
        rm -rf "${PROJECT_DIR}"
        echo "Project files removed."
        echo ""
        echo "========================================="
        echo "Complete uninstallation finished!"
        echo "========================================="
    else
        echo "Project files kept."
        echo ""
        echo "To manually remove later, run:"
        echo "  sudo rm -rf ${PROJECT_DIR}"
    fi
else
    echo ""
    echo "Project files kept at: ${PROJECT_DIR}"
    echo ""
    echo "To manually remove later, run:"
    echo "  sudo rm -rf ${PROJECT_DIR}"
fi

echo ""
echo "Uninstallation completed."
echo ""
