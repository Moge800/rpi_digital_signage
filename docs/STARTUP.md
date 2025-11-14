# Digital Signage - Startup Scripts

## 概要

実機（Raspberry Pi等）でデジタルサイネージを自動起動するためのスクリプト群。

---

## 📁 ファイル構成

| ファイル | 用途 |
|---------|------|
| `scripts/startup.sh` | アプリケーション起動スクリプト |
| `scripts/startup_service.sh` | systemdサービスインストーラー |
| `scripts/uninstall.sh` | アンインストールスクリプト |

---

## 🚀 セットアップ手順

### 1. 必要なパッケージのインストール

```bash
# ディスプレイ管理ツール
sudo apt update
sudo apt install -y unclutter xserver-xorg-video-all

# Chromiumブラウザ（まだの場合）
sudo apt install -y chromium-browser
```

### 2. 実行権限の付与

```bash
chmod +x scripts/*.sh
```

### 3. 手動起動テスト

```bash
# Kioskモードで起動
./scripts/startup.sh
```

**期待される動作**:
- ✅ 仮想環境の確認・作成
- ✅ 依存関係のインストール
- ✅ Kioskモードの有効化
- ✅ ディスプレイ設定（スリープ無効化）
- ✅ マウスカーソル非表示
- ✅ Chromium全画面で起動

---

### 4. 自動起動の設定

```bash
# systemdサービスとして登録
sudo ./scripts/startup_service.sh
```

**実行後の確認**:
```bash
# サービス状態確認
sudo systemctl status digital-signage

# 今すぐ起動
sudo systemctl start digital-signage

# ログ確認
sudo journalctl -u digital-signage -f
```

---

## 🔧 サービス管理コマンド

```bash
# 起動
sudo systemctl start digital-signage

# 停止
sudo systemctl stop digital-signage

# 再起動
sudo systemctl restart digital-signage

# 状態確認
sudo systemctl status digital-signage

# ログ確認（リアルタイム）
sudo journalctl -u digital-signage -f

# 自動起動の有効化
sudo systemctl enable digital-signage

# 自動起動の無効化
sudo systemctl disable digital-signage
```

---

## 🗑️ アンインストール

### 簡単アンインストール（推奨）

```bash
# アンインストールスクリプト実行
sudo ./scripts/uninstall.sh
```

**実行内容**:
1. サービス停止
2. 自動起動無効化
3. サービスファイル削除
4. systemd再読み込み
5. プロジェクトファイル削除の確認（任意）

### 手動アンインストール

```bash
# サービス削除
sudo systemctl stop digital-signage
sudo systemctl disable digital-signage
sudo rm /etc/systemd/system/digital-signage.service
sudo systemctl daemon-reload

# プロジェクトファイル削除（任意）
sudo rm -rf /path/to/rpi_digital_signage
```

---

## 📝 ログファイル

| ファイル | 内容 |
|---------|------|
| `logs/startup.log` | 起動スクリプトのログ |
| `logs/app.log` | アプリケーションログ |
| `logs/service.log` | systemdサービス標準出力 |
| `logs/service_error.log` | systemdサービスエラー出力 |

---

## 🐛 トラブルシューティング

### 1. ディスプレイが表示されない

```bash
# DISPLAY環境変数を確認
echo $DISPLAY  # :0 が表示されるべき

# X11の権限確認
xhost +local:
```

### 2. Chromiumが起動しない

```bash
# Chromiumのインストール確認
which chromium-browser

# 手動起動テスト
chromium-browser --kiosk http://localhost:8501
```

### 3. 自動起動しない

```bash
# サービスの状態確認
sudo systemctl status digital-signage

# ログ確認
sudo journalctl -u digital-signage -n 50

# サービスファイルの確認
cat /etc/systemd/system/digital-signage.service
```

### 4. マウスカーソルが表示される

```bash
# unclutterのインストール
sudo apt install unclutter

# 手動起動
unclutter -idle 0.1 -root &
```

---

## ⚙️ カスタマイズ

### startup.sh の設定変更

```bash
# ログディレクトリの変更
LOG_DIR="${PROJECT_DIR}/logs"

# Kioskモードの強制有効化（.env上書き）
sed -i 's/^KIOSK_MODE=.*/KIOSK_MODE=true/' .env
```

### ディスプレイ設定

```bash
# スクリーンセーバー無効化時間の調整
xset s off
xset -dpms
xset s noblank

# 画面の輝度調整（Raspberry Pi）
echo 255 > /sys/class/backlight/rpi_backlight/brightness
```

---

## 🔒 セキュリティ

### 本番運用時の推奨設定

1. **SSHの無効化** (サイネージ専用機の場合)
```bash
sudo systemctl disable ssh
sudo systemctl stop ssh
```

2. **自動ログイン設定** (Raspberry Pi)
```bash
sudo raspi-config
# 1. System Options
# S5. Boot / Auto Login
# B2. Console Autologin
```

3. **ファイアウォール設定**
```bash
sudo ufw enable
sudo ufw allow from 192.168.0.0/16 to any port 22  # SSH (LAN内のみ)
```

---

## 📌 参考情報

### systemdサービスの仕組み

- **`After=graphical.target`**: GUI起動後に実行
- **`Restart=always`**: クラッシュ時に自動再起動
- **`RestartSec=10`**: 再起動まで10秒待機
- **`WantedBy=graphical.target`**: GUI起動時に自動実行

### 起動順序

```
システム起動
  ↓
graphical.target (GUI起動)
  ↓
digital-signage.service 起動
  ↓
startup.sh 実行
  ↓
  1. 仮想環境確認
  2. 依存関係インストール
  3. Kioskモード有効化
  4. ディスプレイ設定
  5. アプリケーション起動
  ↓
Chromium全画面表示
```

---

## 📞 サポート

問題が発生した場合は、以下の情報を確認してください:

1. ログファイル (`logs/startup.log`, `logs/service.log`)
2. systemdステータス (`sudo systemctl status digital-signage`)
3. ジャーナルログ (`sudo journalctl -u digital-signage -n 100`)

---

**更新日**: 2025-11-14
