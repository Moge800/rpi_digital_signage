# デプロイガイド

Raspberry Pi 5へのデプロイ手順をまとめています。

## 📁 ファイル一覧

### ドキュメント

- **[DEPLOY.md](DEPLOY.md)** - 通常デプロイガイド (インターネット接続可能な環境)
  - システム要件
  - 初回セットアップ手順
  - 自動起動設定 (systemd)
  - キオスクモード設定
  - トラブルシューティング

- **[DEPLOY_OFFLINE.md](DEPLOY_OFFLINE.md)** - オフライン環境デプロイガイド ⭐
  - インターネット接続不可の環境向け
  - USBメモリ経由の転送手順
  - 依存パッケージの事前ダウンロード
  - 完全オフライン構築チェックリスト
  - ゴールデンイメージ作成方法

### スクリプト

#### Windows開発環境用

- **[prepare_offline.ps1](prepare_offline.ps1)** - オフラインデプロイ準備スクリプト
  - Linux ARM64用パッケージの一括ダウンロード
  - プロジェクトアーカイブの自動作成
  - USBメモリ転送用ファイル準備

#### Raspberry Pi用

- **[setup_rpi.sh](setup_rpi.sh)** - 通常セットアップスクリプト (インターネット必須)
  - ワンコマンド自動セットアップ
  - systemdサービス自動作成
  - Streamlit設定自動生成

- **[setup_rpi_offline.sh](setup_rpi_offline.sh)** - オフラインセットアップスクリプト ⭐
  - インターネット不要
  - ローカルパッケージからインストール
  - 事前に `prepare_offline.ps1` で準備したファイルが必要

---

## 🚀 クイックスタート

### ケース1: インターネット接続可能

```bash
# Raspberry Pi上で
git clone https://github.com/Moge800/rpi_digital_signage.git
cd rpi_digital_signage
chmod +x docs/setup_rpi.sh
./docs/setup_rpi.sh
```

詳細は [DEPLOY.md](DEPLOY.md) を参照

---

### ケース2: インターネット接続不可 (工場環境等) ⭐

#### Step 1: Windows開発PCで準備

```powershell
# プロジェクトルートで実行
.\docs\prepare_offline.ps1
```

生成されるファイル:
- `rpi_digital_signage.tar.gz` - プロジェクト一式
- `packages/` - 依存パッケージ (Linux ARM64用)

#### Step 2: USBメモリに転送

以下をUSBメモリにコピー:
- `rpi_digital_signage.tar.gz`
- `packages/` フォルダ
- `docs/setup_rpi_offline.sh`

#### Step 3: Raspberry Pi上で展開・セットアップ

```bash
# USBメモリから転送
cd ~
cp /media/pi/USB_NAME/rpi_digital_signage.tar.gz .
tar -xzf rpi_digital_signage.tar.gz
cd rpi_digital_signage

# packagesフォルダをコピー
cp -r /media/pi/USB_NAME/packages .

# セットアップ実行
chmod +x docs/setup_rpi_offline.sh
./docs/setup_rpi_offline.sh

# .envを編集してPLC接続情報を設定
nano .env

# 起動
python main.py
```

詳細は [DEPLOY_OFFLINE.md](DEPLOY_OFFLINE.md) を参照

---

## 🔧 セットアップ後の確認

### 動作確認

```bash
# ブラウザで以下にアクセス
http://localhost:8501
```

### サービスの状態確認

```bash
sudo systemctl status digital-signage.service
```

### ログの確認

```bash
# アプリケーションログ
cat ~/rpi_digital_signage/logs/app.log
cat ~/rpi_digital_signage/logs/plc.log

# systemdログ
sudo journalctl -u digital-signage.service -f
```

---

## 📝 よくある質問

### Q: PLC接続エラーが出る

```bash
# ネットワーク疎通確認
ping <PLC_IP>

# .env設定確認
cat .env

# DEBUG_DUMMY_READ=true に設定してダミーデータで動作確認
```

### Q: Streamlitが起動しない

```bash
# ポート使用確認
sudo lsof -i :8501

# 既存プロセスの終了
pkill -f streamlit

# サービス再起動
sudo systemctl restart digital-signage.service
```

### Q: 複数台のラズパイにデプロイしたい

1. 1台目で完全セットアップ
2. SDカードイメージをバックアップ
3. 他のラズパイに同じイメージを焼く
4. 各ラズパイで `.env` の `PLC_IP` と `LINE_NAME` のみ変更

詳細は [DEPLOY_OFFLINE.md](DEPLOY_OFFLINE.md) の「ゴールデンイメージ作成」を参照

---

## 📞 トラブルシューティング

詳細なトラブルシューティングは各ガイドを参照:
- [DEPLOY.md - トラブルシューティング](DEPLOY.md#トラブルシューティング)
- [DEPLOY_OFFLINE.md - トラブルシューティング](DEPLOY_OFFLINE.md#トラブルシューティング)

---

## 🔒 セキュリティ注意事項

- `.env` ファイルには機密情報 (PLC IP等) が含まれるため、管理に注意
- USBメモリ転送時は紛失・盗難に注意
- 不要になったUSBメモリは確実にデータ消去
- オフライン環境でのシャドーITは**セキュリティポリシーに従う**こと

---

**工場のオフライン環境でも安全にデプロイできるよう設計されています！** 🏭
