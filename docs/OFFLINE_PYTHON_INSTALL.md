# Python 3.11 オフラインインストールガイド

## 概要

オフライン環境のRaspberry Pi 5にPython 3.11をインストールするための手順書です。

> **Note**: Raspberry Pi OS Bookwormには標準でPython 3.11が含まれています。
> オフライン環境でのパッケージ準備が主な目的です。

## 前提条件

- **開発環境**: Windows (WSLインストール済み) または Linux/Ubuntu
- **転送媒体**: USBメモリ (容量: 500MB以上推奨)
- **対象環境**: Raspberry Pi 5 (Raspberry Pi OS Bookworm 64-bit)

---

## 手順1: Windows環境でパッケージをダウンロード

### 1-1. WSLの確認・インストール

```powershell
# WSLがインストールされているか確認
wsl --version

# インストールされていない場合
wsl --install
# PC再起動が必要
```

### 1-2. ダウンロードスクリプト実行 (PowerShell)

```powershell
# プロジェクトのscriptsディレクトリに移動
cd C:\Users\<username>\Develop\rpi_digital_signage\scripts

# PowerShellスクリプト実行
.\download_python_packages_windows.ps1
```

**実行内容**:
- WSL (Ubuntu) 経由でDebian/Ubuntuリポジトリから以下をダウンロード:
  - `python3.11` 本体 (または最新の3.x)
  - `python3.11-venv` (仮想環境)
  - `python3.11-dev` (開発ヘッダー)
  - `build-essential` (gcc, g++, makeなど)
  - 依存ライブラリ (libffi, libssl, zlib等)
  - すべての依存パッケージ (.deb)

**生成ファイル**:
- `python_packages/` - パッケージディレクトリ
- `python_packages.tar.gz` - 圧縮アーカイブ (約100-300MB)

---

## 手順2: Linux/WSL環境で直接ダウンロード (代替方法)

Windowsを使わずWSL/Linux環境で直接実行する場合:

```bash
# scriptsディレクトリに移動
cd /path/to/rpi_digital_signage/scripts

# 実行権限付与
chmod +x download_python_packages.sh

# スクリプト実行
./download_python_packages.sh
```

---

## 手順3: Raspberry Piへ転送

### 3-1. USBメモリにコピー

```powershell
# Windows環境
Copy-Item python_packages.tar.gz E:\
# (E:\ はUSBメモリのドライブレター)
```

### 3-2. Raspberry Piでマウント

```bash
# Raspberry Pi上で
# USBメモリは通常 /media/pi/<device_name> に自動マウント
ls /media/pi/

# ホームディレクトリにコピー
cp /media/pi/*/python_packages.tar.gz ~/
cd ~
```

---

## 手順4: Raspberry Piでインストール

### 4-1. アーカイブ展開

```bash
tar -xzf python_packages.tar.gz
cd python_packages
```

### 4-2. インストールスクリプト実行

```bash
# root権限で実行 (パスワード入力が必要)
sudo ./install_python.sh
```

**実行内容**:
1. すべての.debパッケージをdpkgでインストール
2. 依存関係エラーがあれば自動修復試行
3. Python 3.11インストール確認
4. テスト用仮想環境作成・動作確認

**インストールログ**: `install.log` に保存されます

### 4-3. インストール確認

```bash
# Python 3.11バージョン確認
python3.11 --version
# 出力例: Python 3.11.x

# または標準pythonコマンド
python3 --version

# venvモジュール確認
python3.11 -m venv --help
```

---

## 手順5: プロジェクト環境セットアップ

### 5-1. プロジェクトディレクトリに移動

```bash
cd ~/rpi_digital_signage
```

### 5-2. 仮想環境作成 (Python 3.13使用)

```bash
# Python 3.11で仮想環境作成
python3.11 -m venv .venv
# または標準pythonコマンド
python3 -m venv .venv

source .venv/bin/activate
```

### 5-3. uvインストール

```bash
# pip経由でuvをインストール
pip install uv

# uvバージョン確認
uv --version
```

### 5-4. プロジェクト依存関係インストール

```bash
# pyproject.tomlからすべての依存関係をインストール
uv sync

# インストール確認
uv pip list
```

---

## トラブルシューティング

### ケース1: Python 3.13がリポジトリに存在しない

**症状**:
```
⚠ python3.13がリポジトリに見つかりません
```

**対処法**:

#### オプションA: Python 3.11を使用 (推奨)

スクリプト実行時に選択肢が表示されます:
```
Python 3.11でダウンロードしますか? (y/N): y
```

プロジェクト側で`pyproject.toml`を修正:
```toml
requires-python = ">=3.11"  # 3.13 → 3.11
```

#### オプションB: deadsnakes PPAを使用 (Ubuntu/WSL)

```bash
# WSL/Ubuntu環境で
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update

# その後、ダウンロードスクリプト再実行
./download_python313_packages.sh
```

#### オプションC: ソースからビルド (上級者向け)

Raspberry Pi上でPython 3.13をソースからコンパイル:
```bash
# ビルド依存関係インストール (オンライン環境で実施)
sudo apt-get install build-essential zlib1g-dev libncurses5-dev \
    libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev wget

# Python 3.13ソースダウンロード
wget https://www.python.org/ftp/python/3.13.0/Python-3.13.0.tgz
tar -xf Python-3.13.0.tgz
cd Python-3.13.0

# ビルド・インストール
./configure --enable-optimizations
make -j4
sudo make altinstall
```

### ケース2: 依存関係エラー

**症状**:
```
dpkg: dependency problems prevent configuration
```

**対処法**:
```bash
# 自動修復
sudo apt-get install -f -y

# 強制的に依存関係無視 (最終手段)
cd python313_packages/debs
sudo dpkg -i --force-depends *.deb
```

### ケース3: ディスク容量不足

**確認**:
```bash
df -h
```

**対処法**:
```bash
# 不要パッケージ削除
sudo apt-get autoremove
sudo apt-get clean

# ログファイル削除
sudo journalctl --vacuum-time=7d
```

---

## 補足情報

### パッケージ内容

- **python3.13**: Python 3.13インタープリタ本体
- **python3.13-venv**: 仮想環境作成モジュール
- **python3.13-dev**: C拡張開発用ヘッダー (uv, Cython等で必要)
- **build-essential**: gcc, g++, make (pymcprotocol等のビルド用)
- **libffi-dev, libssl-dev**: 暗号化・FFIライブラリ (Pydantic, uvicorn等)

### 容量目安

- ダウンロードパッケージ: 約150-300MB (圧縮後)
- 展開後: 約400-600MB
- インストール後: 約500-800MB

### セキュリティ注意

- オフラインインストールでは`apt-get update`によるセキュリティパッチ適用ができません
- 定期的にオンライン環境で`sudo apt-get upgrade`を実行することを推奨

---

## 参考資料

- [Raspberry Pi OS公式ドキュメント](https://www.raspberrypi.com/documentation/computers/os.html)
- [Python公式ダウンロード](https://www.python.org/downloads/)
- [deadsnakes PPA](https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa)
- [本プロジェクトREADME](../README.md)
- [デプロイガイド](../docs/DEPLOY.md)
