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

1. `.env.example` を `.env` にコピー
2. `.env` を編集してPLC接続情報とテーマを設定
   ```env
   THEME=dark  # dark または light
   ```
3. `python main.py` で起動

詳細は [docs/README.md](docs/README.md) を参照してください。

## ライセンス

MIT License - 詳細は [LICENSE](LICENSE) をご覧ください。
