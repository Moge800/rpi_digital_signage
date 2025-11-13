# Windows デジタルサイネージ起動スクリプト (PowerShell)
# 
# 使い方:
#   .\launcher.ps1

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Green
Write-Host "デジタルサイネージ起動スクリプト (Windows)" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# プロジェクトルートに移動
$scriptDir = $PSScriptRoot
Set-Location $scriptDir

Write-Host "[1/4] 環境確認" -ForegroundColor Yellow

# Python 3.13確認
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "エラー: pythonコマンドが見つかりません" -ForegroundColor Red
    Write-Host "Python 3.13をインストールしてください" -ForegroundColor Yellow
    Write-Host "  https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

$pythonVersion = python --version
if ($pythonVersion -notmatch "3\.13") {
    Write-Host "警告: Python 3.13が推奨されています" -ForegroundColor Yellow
    Write-Host "現在のバージョン: $pythonVersion" -ForegroundColor Yellow
}

Write-Host "✓ $pythonVersion" -ForegroundColor Green

# .envファイル確認
if (-not (Test-Path ".env")) {
    Write-Host "エラー: .envファイルが見つかりません" -ForegroundColor Red
    Write-Host "セットアップ方法:" -ForegroundColor Yellow
    Write-Host "  Copy-Item .env.example .env" -ForegroundColor White
    Write-Host "  notepad .env  # 設定を編集" -ForegroundColor White
    exit 1
}

Write-Host "✓ .envファイル確認" -ForegroundColor Green

Write-Host ""
Write-Host "[2/4] 仮想環境確認" -ForegroundColor Yellow

# 仮想環境作成・アクティベート
if (-not (Test-Path ".venv")) {
    Write-Host "仮想環境を作成します..." -ForegroundColor Yellow
    python -m venv .venv
}

# 仮想環境アクティベート
& .\.venv\Scripts\Activate.ps1

Write-Host "✓ 仮想環境アクティベート完了" -ForegroundColor Green
$venvPython = python --version
Write-Host "  Python: $venvPython" -ForegroundColor Cyan

Write-Host ""
Write-Host "[3/4] 依存関係確認" -ForegroundColor Yellow

# uvインストール確認
$uvCmd = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvCmd) {
    Write-Host "uvをインストールします..." -ForegroundColor Yellow
    pip install uv
}

$uvVersion = uv --version
Write-Host "✓ $uvVersion" -ForegroundColor Green

# 依存関係同期
Write-Host "依存関係を同期します..." -ForegroundColor Yellow
uv sync

Write-Host ""
Write-Host "[4/4] アプリケーション起動" -ForegroundColor Yellow
Write-Host ""

# main.py実行
python main.py
