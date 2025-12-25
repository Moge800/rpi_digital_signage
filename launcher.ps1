# Windows デジタルサイネージ起動スクリプト
# 
# main.py を通じて FastAPI + Streamlit + Kioskブラウザを起動します。
# 
# 使い方:
#   .\launcher.ps1

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Green
Write-Host "デジタルサイネージ起動スクリプト" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# プロジェクトルートに移動
$scriptDir = $PSScriptRoot
Set-Location $scriptDir

Write-Host "[1/3] 環境確認" -ForegroundColor Yellow

# Python確認
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "エラー: pythonコマンドが見つかりません" -ForegroundColor Red
    exit 1
}

$pythonVersion = python --version
Write-Host "✓ $pythonVersion" -ForegroundColor Green

# .envファイル確認
if (-not (Test-Path ".env")) {
    Write-Host "エラー: .envファイルが見つかりません" -ForegroundColor Red
    Write-Host "セットアップ方法:" -ForegroundColor Yellow
    Write-Host "  Copy-Item .env.example .env"
    Write-Host "  # .env を編集して設定"
    exit 1
}

Write-Host "✓ .envファイル確認" -ForegroundColor Green

Write-Host ""
Write-Host "[2/3] 仮想環境確認" -ForegroundColor Yellow

# 仮想環境作成
if (-not (Test-Path ".venv")) {
    Write-Host "仮想環境を作成します..." -ForegroundColor Yellow
    python -m venv .venv
}

# 仮想環境アクティベート
& .\.venv\Scripts\Activate.ps1
Write-Host "✓ 仮想環境アクティベート完了" -ForegroundColor Green

# uvインストール確認
$uvCmd = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvCmd) {
    Write-Host "uvをインストールします..." -ForegroundColor Yellow
    pip install uv
}

Write-Host "✓ uv $(uv --version)" -ForegroundColor Green
Write-Host "依存関係を同期します..." -ForegroundColor Yellow
uv sync

Write-Host ""
Write-Host "[3/3] アプリケーション起動" -ForegroundColor Yellow
Write-Host ""

# --watchdog オプションでWatchdogモード（API監視付き）起動
$watchdogMode = $args -contains "--watchdog"

# main.py を実行 (Pythonランチャーに処理を委譲)
try {
    if ($watchdogMode) {
        Write-Host "Watchdogモードで起動します (API監視付き)" -ForegroundColor Green
        uv run python main.py --watchdog
    } else {
        Write-Host "通常モードで起動します" -ForegroundColor Green
        uv run python main.py
    }
} catch {
    Write-Host "エラー: アプリケーションの起動に失敗しました" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
