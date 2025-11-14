#!/bin/bash
# Systemd Service Installer for Digital Signage
# Run this script once to set up auto-start on boot

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="digital-signage"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "========================================="
echo "Digital Signage Service Installer"
echo "========================================="
echo "Project directory: ${PROJECT_DIR}"
echo ""

# root権限チェック
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root"
    echo "Please run: sudo $0"
    exit 1
fi

# ユーザー名を取得（sudoで実行された場合の実際のユーザー）
ACTUAL_USER="${SUDO_USER:-$USER}"
echo "Service will run as user: ${ACTUAL_USER}"

# サービスファイル作成
echo "Creating systemd service file..."
cat > "${SERVICE_FILE}" << EOF
[Unit]
Description=Digital Signage System
After=network.target graphical.target
Wants=graphical.target

[Service]
Type=simple
User=${ACTUAL_USER}
WorkingDirectory=${PROJECT_DIR}
Environment="DISPLAY=:0"
Environment="XAUTHORITY=/home/${ACTUAL_USER}/.Xauthority"
ExecStart=${PROJECT_DIR}/startup.sh
Restart=always
RestartSec=10
StandardOutput=append:${PROJECT_DIR}/logs/service.log
StandardError=append:${PROJECT_DIR}/logs/service_error.log

[Install]
WantedBy=graphical.target
EOF

echo "Service file created: ${SERVICE_FILE}"

# startup.shに実行権限付与
echo "Setting execute permission on startup.sh..."
chmod +x "${PROJECT_DIR}/startup.sh"

# systemdに反映
echo "Reloading systemd daemon..."
systemctl daemon-reload

# サービスを有効化
echo "Enabling service..."
systemctl enable "${SERVICE_NAME}.service"

echo ""
echo "========================================="
echo "Installation completed!"
echo "========================================="
echo ""
echo "Service commands:"
echo "  Start:   sudo systemctl start ${SERVICE_NAME}"
echo "  Stop:    sudo systemctl stop ${SERVICE_NAME}"
echo "  Status:  sudo systemctl status ${SERVICE_NAME}"
echo "  Logs:    sudo journalctl -u ${SERVICE_NAME} -f"
echo ""
echo "The service will start automatically on next boot."
echo ""
echo "To start now, run:"
echo "  sudo systemctl start ${SERVICE_NAME}"
echo ""
