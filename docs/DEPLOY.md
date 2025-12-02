# Raspberry Pi 5 デプロイガイド

## 前提条件

- Raspberry Pi OS (64-bit) Bookworm以降
- Python 3.11+ (Bookwormには標準で含まれています)
- ネットワーク接続 (初回セットアップ時)
- PLC(MELSEC)との通信可能なネットワーク環境

⚠️ **オフライン環境の場合**: [オフラインインストールガイド](OFFLINE_PYTHON_INSTALL.md)を参照

## 初回セットアップ

### 方法A: オンライン環境 (推奨)

#### 1. システムパッケージの更新

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip git
```

> **Note**: Raspberry Pi OS BookwormにはPython 3.11が標準で含まれています。

#### 2. uvのインストール

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

#### 3. プロジェクトのクローン

```bash
cd ~
git clone https://github.com/Moge800/rpi_digital_signage.git
cd rpi_digital_signage
```

#### 4. 仮想環境のセットアップ

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install uv
uv sync
```

### 方法B: オフライン環境

**詳細手順**: [docs/OFFLINE_PYTHON_INSTALL.md](OFFLINE_PYTHON_INSTALL.md)

**要約**:
1. Windows/WSL環境で `scripts/download_python_packages_windows.ps1` を実行
2. 生成された `python_packages.tar.gz` をUSBメモリでRaspberry Piに転送
3. Raspberry Pi上で展開・インストール:
   ```bash
   tar -xzf python_packages.tar.gz
   cd python_packages
   sudo ./install_python.sh
   ```
4. プロジェクトディレクトリで依存関係インストール:
   ```bash
   cd ~/rpi_digital_signage
   python3 -m venv .venv
   source .venv/bin/activate
   pip install uv
   uv sync
   ```

### 5. 環境変数の設定

```bash
cp .env.example .env
nano .env  # または vim .env
```

以下の項目を設定:
```env
# PLC接続設定
PLC_IP=192.168.1.100        # PLCのIPアドレス
PLC_PORT=5000               # PLCのポート番号
AUTO_RECONNECT=true
RECONNECT_RETRY=5
RECONNECT_DELAY=3.0

# デバッグ設定
DEBUG_DUMMY_READ=false      # 本番環境ではfalse

# アプリケーション設定
USE_PLC=true                # 本番環境ではtrue
LINE_NAME=生産ライン1        # 表示するライン名
REFRESH_INTERVAL=10         # 更新間隔（秒）
LOG_LEVEL=INFO              # ログレベル
```

## 起動方法

### 手動起動

```bash
cd ~/rpi_digital_signage
python main.py
```

または

```bash
.venv/bin/streamlit run src/frontend/signage_app.py
```

ブラウザで `http://localhost:8501` にアクセス

### 自動起動設定 (systemd)

#### サービスファイルの作成

```bash
sudo nano /etc/systemd/system/digital-signage.service
```

以下の内容を記述:

```ini
[Unit]
Description=Digital Signage System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/rpi_digital_signage
Environment="PATH=/home/pi/rpi_digital_signage/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/pi/rpi_digital_signage/.venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### サービスの有効化と起動

```bash
sudo systemctl daemon-reload
sudo systemctl enable digital-signage.service
sudo systemctl start digital-signage.service
```

#### サービスの状態確認

```bash
sudo systemctl status digital-signage.service
```

#### ログの確認

```bash
sudo journalctl -u digital-signage.service -f
```

## キオスクモード設定 (フルスクリーン表示)

### Chromiumの自動起動

```bash
mkdir -p ~/.config/autostart
nano ~/.config/autostart/kiosk.desktop
```

以下の内容を記述:

```desktop
[Desktop Entry]
Type=Application
Name=Kiosk Browser
Exec=chromium-browser --kiosk --app=http://localhost:8501
X-GNOME-Autostart-enabled=true
```

### 画面スリープの無効化

```bash
sudo raspi-config
# Display Options > Screen Blanking > No
```

## トラブルシューティング

### PLC接続エラー

```bash
# ネットワーク疎通確認
ping <PLC_IP>

# ポート確認
nc -zv <PLC_IP> <PLC_PORT>

# ログ確認
cat logs/plc.log
```

### Streamlit起動失敗

```bash
# ポート使用状況確認
sudo lsof -i :8501

# プロセスの強制終了
pkill -f streamlit
```

### メモリ不足

Raspberry Pi 5は8GBモデル推奨。4GBモデルの場合はスワップを増やす:

```bash
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# CONF_SWAPSIZE=2048 に変更
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

## 更新手順

```bash
cd ~/rpi_digital_signage
git pull
uv sync
sudo systemctl restart digital-signage.service
```

## パフォーマンス最適化

### Streamlit設定

`~/.streamlit/config.toml` を作成:

```toml
[server]
headless = true
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false
```

### GPU有効化

```bash
sudo raspi-config
# Advanced Options > GL Driver > GL (Full KMS)
```

## セキュリティ

- `.env`ファイルのパーミッション確認: `chmod 600 .env`
- ファイアウォール設定 (必要に応じて):
  ```bash
  sudo ufw allow 8501/tcp  # Streamlit
  sudo ufw allow from <PLC_IP>  # PLC通信
  sudo ufw enable
  ```

## バックアップ

```bash
# 設定ファイルのバックアップ
tar -czf backup_$(date +%Y%m%d).tar.gz .env logs/
```
