# Python 3.13 オフラインインストール - スクリプト説明

## 概要

このディレクトリには、オフライン環境のRaspberry PiにPython 3.13をインストールするためのスクリプトが含まれています。

## スクリプト一覧

### 1. `download_python313_packages_windows.ps1` (Windows PowerShell)

**用途**: Windows環境でWSL経由でパッケージをダウンロード

**前提条件**:
- Windows 10/11
- WSL (Ubuntu推奨) インストール済み

**実行方法**:
```powershell
.\download_python313_packages_windows.ps1
```

**生成物**:
- `python313_packages/` - パッケージディレクトリ
- `python313_packages.tar.gz` - 圧縮アーカイブ (Raspberry Piに転送)

---

### 2. `download_python313_packages.sh` (Linux/WSL Bash)

**用途**: Linux/WSL環境で直接パッケージをダウンロード

**前提条件**:
- Ubuntu/Debian系Linux
- apt パッケージマネージャ

**実行方法**:
```bash
chmod +x download_python313_packages.sh
./download_python313_packages.sh
```

**処理フロー**:
1. apt-get update でリポジトリ更新
2. Python 3.13関連パッケージをダウンロード:
   - python3.13
   - python3.13-venv
   - python3.13-dev
   - build-essential (gcc, g++, make)
   - 開発ライブラリ (libffi, libssl, zlib等)
3. すべての依存パッケージも再帰的にダウンロード
4. インストールスクリプト (`install_python313.sh`) 生成
5. tar.gz形式で圧縮

**生成物**:
- `python313_packages/debs/` - .debファイル群
- `python313_packages/install_python313.sh` - Raspberry Pi用インストーラー
- `python313_packages.tar.gz` - 圧縮アーカイブ

---

### 3. `install_python313.sh` (自動生成)

**用途**: Raspberry Pi上でパッケージをインストール

**実行環境**: Raspberry Pi OS (Bookworm)

**実行方法**:
```bash
# アーカイブ展開後
cd python313_packages
sudo ./install_python313.sh
```

**処理フロー**:
1. root権限チェック
2. すべての.debパッケージをdpkgでインストール
3. 依存関係エラーがあれば `apt-get install -f` で自動修復
4. Python 3.13インストール確認
5. テスト用仮想環境作成・動作検証

**ログ出力**: `install.log` にインストール詳細を記録

---

## 使用フロー (全体)

```
[Windows/Linux PC]
    ↓
(1) download_python313_packages_windows.ps1 実行
    ↓
  python313_packages.tar.gz 生成
    ↓
  USBメモリにコピー
    ↓
[Raspberry Pi]
    ↓
(2) tar -xzf python313_packages.tar.gz
    ↓
(3) sudo ./install_python313.sh
    ↓
  Python 3.13インストール完了
    ↓
(4) プロジェクトセットアップ
    python3.13 -m venv .venv
    source .venv/bin/activate
    pip install uv
    uv sync
```

---

## トラブルシューティング

### Q1: Python 3.13がリポジトリに見つからない

**回答**: Raspberry Pi OS Bookwormでは標準リポジトリにPython 3.13がない可能性があります。

**対処法**:
- **オプション1**: スクリプト実行時にPython 3.11を選択 (互換性あり)
- **オプション2**: Ubuntu PPAを使用 (WSL環境)
  ```bash
  sudo add-apt-repository ppa:deadsnakes/ppa
  sudo apt-get update
  ```
- **オプション3**: ソースからビルド (時間がかかる)

### Q2: WSLが見つからない (Windows)

**回答**:
```powershell
# WSLインストール
wsl --install

# PC再起動後、Ubuntuセットアップ
wsl --install -d Ubuntu
```

### Q3: dpkgで依存関係エラー

**回答**:
```bash
# 自動修復
sudo apt-get install -f -y

# 強制インストール (最終手段)
sudo dpkg -i --force-depends debs/*.deb
```

---

## セキュリティ考慮事項

- オフラインパッケージは**ダウンロード時点のバージョン**です
- セキュリティパッチは含まれていません
- 定期的にオンライン環境で `sudo apt-get update && sudo apt-get upgrade` 実行を推奨

---

## 関連ドキュメント

- [OFFLINE_PYTHON_INSTALL.md](../docs/OFFLINE_PYTHON_INSTALL.md) - 詳細インストールガイド
- [DEPLOY.md](../docs/DEPLOY.md) - Raspberry Piデプロイガイド
- [README.md](../README.md) - プロジェクト概要

---

## ライセンス

このスクリプトはプロジェクトと同じMITライセンスです。
