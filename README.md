# Raspberry Pi Digital Signage

🚧 **このプロジェクトは現在開発中です** 🚧

[![Test](https://github.com/Moge800/rpi_digital_signage/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/Moge800/rpi_digital_signage/actions/workflows/test.yml)
[![Lint](https://github.com/Moge800/rpi_digital_signage/actions/workflows/lint.yml/badge.svg?branch=main)](https://github.com/Moge800/rpi_digital_signage/actions/workflows/lint.yml)

生産ラインの進捗状況をリアルタイムで表示するデジタルサイネージシステム

## 機能

- **リアルタイム生産モニタリング**: PLC (MELSEC) から生産データを取得し表示
- **テーマ切り替え**: ダークモード/ライトモードをサポート (`.env`で設定可能)
- **フルHD対応**: 1920x1080 解像度に最適化

## セットアップ

### オフライン環境 (Raspberry Pi)

オフライン環境でPythonをインストールする場合:

📖 **[オフラインインストールガイド](docs/OFFLINE_PYTHON_INSTALL.md)** を参照

### オンライン環境

1. Python 3.11以上のインストール
   ```bash
   python3 --version  # バージョン確認 (3.11以上)
   ```

2. `.env.example` を `.env` にコピー
   ```bash
   cp .env.example .env
   ```

3. `.env` を編集してPLC接続情報とテーマを設定
   ```env
   THEME=dark  # dark または light
   PLC_IP=192.168.0.10
   PLC_PORT=5000
   ```

4. 依存関係インストール
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install uv
   uv sync
   ```

5. アプリケーション起動
   ```bash
   python main.py
   ```

詳細は [docs/README.md](docs/README.md) を参照してください。

## ライセンス

MIT License - 詳細は [LICENSE](LICENSE) をご覧ください。
