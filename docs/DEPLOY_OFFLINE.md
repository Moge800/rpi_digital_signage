# オフライン環境デプロイガイド

## 🚫 インターネット接続不可の環境での導入手順

工場内のセキュリティポリシーでインターネット接続が制限されている場合の手順です。

---

## 前提条件

- **開発PC**: インターネット接続可能なWindows環境
- **Raspberry Pi**: インターネット接続不可
- **転送手段**: USBメモリ、または一時的な内部ネットワーク経由

---

## ステップ1: 開発PCでパッケージを準備

### 1.1 依存パッケージのダウンロード

```powershell
# プロジェクトディレクトリで実行
cd C:\Users\benom\Develop\rpi_digital_signage

# 依存パッケージをダウンロード (Linux ARM64用)
uv pip download -r pyproject.toml --platform linux --python-version 3.13 --dest packages/
```

または、手動で全パッケージをダウンロード:

```powershell
# packages ディレクトリを作成
mkdir packages

# 各パッケージをダウンロード
uv pip download plotly pydantic-settings pymcprotocol python-dotenv streamlit streamlit-autorefresh --platform linux --python-version 3.13 --dest packages/
```

### 1.2 uvインストーラーのダウンロード

```powershell
# uvのスタンドアロンバイナリをダウンロード
curl -LsSf https://astral.sh/uv/install.sh -o uv_install.sh
```

または、[https://github.com/astral-sh/uv/releases](https://github.com/astral-sh/uv/releases) から `uv-aarch64-unknown-linux-gnu.tar.gz` を手動ダウンロード

### 1.3 プロジェクトファイルの準備

```powershell
# .envファイルの準備 (機密情報に注意)
cp .env.example .env
# .envを編集してPLC情報を設定

# 転送用にアーカイブ作成
tar -czf rpi_digital_signage.tar.gz --exclude=.venv --exclude=.git --exclude=__pycache__ --exclude=logs --exclude=.mypy_cache .
```

---

## ステップ2: Raspberry Piへ転送

### 方法A: USBメモリ

1. 以下をUSBメモリにコピー:
   - `rpi_digital_signage.tar.gz`
   - `packages/` フォルダ
   - `uv_install.sh` または uvバイナリ

2. USBメモリをRaspberry Piに挿入

```bash
# Raspberry Pi上で
cd ~
cp /media/pi/USB_NAME/rpi_digital_signage.tar.gz .
cp -r /media/pi/USB_NAME/packages .
cp /media/pi/USB_NAME/uv_install.sh .
```

### 方法B: ローカルネットワーク (scp)

内部ネットワークのみ接続可能な場合:

```powershell
# 開発PCから
scp rpi_digital_signage.tar.gz pi@<RASPBERRY_PI_IP>:~
scp -r packages pi@<RASPBERRY_PI_IP>:~
scp uv_install.sh pi@<RASPBERRY_PI_IP>:~
```

---

## ステップ3: Raspberry Pi上でセットアップ

### 3.1 uvのインストール (オフライン)

```bash
# バイナリを展開
tar -xzf uv-aarch64-unknown-linux-gnu.tar.gz
sudo mv uv /usr/local/bin/
chmod +x /usr/local/bin/uv
```

### 3.2 プロジェクトの展開

```bash
cd ~
tar -xzf rpi_digital_signage.tar.gz
cd rpi_digital_signage
```

### 3.3 仮想環境の作成とパッケージインストール

```bash
# 仮想環境作成
python3 -m venv .venv
source .venv/bin/activate

# ローカルパッケージからインストール
pip install --no-index --find-links=../packages plotly pydantic-settings pymcprotocol python-dotenv streamlit streamlit-autorefresh
```

### 3.4 .envの確認と編集

```bash
# PLC接続情報を確認
nano .env
```

### 3.5 動作確認

```bash
python main.py
```

---

## ステップ4: 自動起動設定

### systemdサービスの作成

```bash
sudo nano /etc/systemd/system/digital-signage.service
```

以下を記述:

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

有効化:

```bash
sudo systemctl daemon-reload
sudo systemctl enable digital-signage.service
sudo systemctl start digital-signage.service
```

---

## トラブルシューティング

### 依存パッケージのエラー

```bash
# 不足パッケージの確認
pip list
python -c "import streamlit; import plotly; import pymcprotocol"
```

エラーが出た場合、開発PCで追加パッケージをダウンロードして再転送:

```powershell
# 開発PC
uv pip download <パッケージ名> --platform linux --dest packages/
```

### Python バージョン不一致

Raspberry Pi OSのPythonバージョンが3.13未満の場合:

```bash
# Pythonバージョン確認
python3 --version

# 3.11など古い場合、pyproject.tomlを一時的に修正
nano pyproject.toml
# requires-python = ">=3.11" に変更
```

### システムパッケージが必要な場合

一部のパッケージ(plotlyなど)はシステムライブラリに依存する場合があります。

**事前準備** (インターネット接続可能な環境で):

Raspberry Pi OSイメージ作成時に、以下をインストール済みにしておく:

```bash
sudo apt install -y python3-pip python3-venv python3-dev build-essential
```

---

## 更新手順 (オフライン)

### コード更新のみ

1. 開発PCで修正・テスト
2. 変更ファイルのみをUSBで転送
3. Raspberry Pi上で上書き
4. サービス再起動

```bash
sudo systemctl restart digital-signage.service
```

### パッケージ更新が必要な場合

1. 開発PCで新パッケージをダウンロード
2. Raspberry Piへ転送
3. `pip install --no-index --find-links=...` で再インストール

---

## 完全オフライン構築のチェックリスト

- [ ] プロジェクトコード一式
- [ ] `.env`ファイル (PLC接続情報設定済み)
- [ ] Pythonパッケージ (packages/ ディレクトリ)
- [ ] uvバイナリ (または pip使用)
- [ ] Raspberry Pi OSイメージ (python3-venv等インストール済み)
- [ ] USBメモリまたは転送手段
- [ ] DEPLOY_OFFLINE.md (このファイル)

---

## シャドーIT運用の場合

**スマホテザリング等で一時的にインターネット接続する場合:**

```bash
# Raspberry Piをスマホテザリングに接続
# Wi-Fi設定から一時的に接続

# 通常のセットアップスクリプトを実行
./setup_rpi.sh

# セットアップ完了後、Wi-Fi切断
# 以降はオフラインで動作
```

⚠️ **注意**: セキュリティポリシー違反にならないよう、情シス部門に確認してください。

---

## 推奨: ゴールデンイメージ作成

頻繁にデプロイする場合、環境構築済みのRaspberry Pi OSイメージを作成:

1. 1台のRaspberry Piで完全セットアップ
2. SDカードイメージをバックアップ
3. 他のRaspberry Piに同じイメージを書き込み
4. `.env`の`PLC_IP`だけ個別設定

これで2台目以降は5分で完了します。
