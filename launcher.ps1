# Windows デジタルサイネージ起動スクリプト (FastAPI + Streamlit 2プロセス構成)
# 
# 使い方:
#   .\launcher_new.ps1

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Green
Write-Host "デジタルサイネージ起動スクリプト" -ForegroundColor Green
Write-Host "(FastAPI + Streamlit 構成)" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# プロジェクトルートに移動
$scriptDir = $PSScriptRoot
Set-Location $scriptDir

# 設定
$API_HOST = if ($env:API_HOST) { $env:API_HOST } else { "127.0.0.1" }
$API_PORT = if ($env:API_PORT) { $env:API_PORT } else { "8000" }
$STREAMLIT_PORT = if ($env:STREAMLIT_PORT) { $env:STREAMLIT_PORT } else { "8501" }

# 初期化フラグをクリア
$tempPath = [System.IO.Path]::GetTempPath()
Remove-Item "$tempPath\signage_initialized.flag" -ErrorAction SilentlyContinue
Remove-Item "$tempPath\signage_frontend_initialized.flag" -ErrorAction SilentlyContinue

# グローバル変数でプロセス管理
$script:apiProcess = $null
$script:streamlitProcess = $null

# クリーンアップ関数
function Cleanup {
    Write-Host ""
    Write-Host "シャットダウン中..." -ForegroundColor Yellow
    
    # Streamlit停止
    if ($script:streamlitProcess -and !$script:streamlitProcess.HasExited) {
        Write-Host "Streamlitを停止中..." -ForegroundColor Yellow
        $script:streamlitProcess.Kill()
        $script:streamlitProcess.WaitForExit(5000)
    }
    
    # API停止（シャットダウンエンドポイント経由）
    if ($script:apiProcess -and !$script:apiProcess.HasExited) {
        Write-Host "APIサーバーを停止中..." -ForegroundColor Yellow
        try {
            Invoke-RestMethod -Uri "http://${API_HOST}:${API_PORT}/api/shutdown" -Method POST -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        } catch {}
        
        if (!$script:apiProcess.HasExited) {
            $script:apiProcess.Kill()
            $script:apiProcess.WaitForExit(5000)
        }
    }
    
    Write-Host "シャットダウン完了" -ForegroundColor Green
}

# Ctrl+Cハンドラ
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Cleanup }

Write-Host "[1/4] 環境確認" -ForegroundColor Yellow

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
    exit 1
}

Write-Host "✓ .envファイル確認" -ForegroundColor Green

Write-Host ""
Write-Host "[2/4] 仮想環境確認" -ForegroundColor Yellow

# 仮想環境作成
if (-not (Test-Path ".venv")) {
    Write-Host "仮想環境を作成します..." -ForegroundColor Yellow
    python -m venv .venv
}

# 仮想環境アクティベート
& .\.venv\Scripts\Activate.ps1
Write-Host "✓ 仮想環境アクティベート完了" -ForegroundColor Green

Write-Host ""
Write-Host "[3/4] 依存関係確認" -ForegroundColor Yellow

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
Write-Host "========================================" -ForegroundColor Green
Write-Host "[4/4] アプリケーション起動" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# APIサーバー起動
Write-Host "APIサーバーを起動中... (${API_HOST}:${API_PORT})" -ForegroundColor Yellow
$script:apiProcess = Start-Process -FilePath "uv" -ArgumentList "run", "uvicorn", "src.api.main:app", "--host", $API_HOST, "--port", $API_PORT -PassThru -NoNewWindow
Write-Host "✓ APIサーバー起動 (PID: $($script:apiProcess.Id))" -ForegroundColor Green

# APIサーバーの起動を待つ
Write-Host "APIサーバーの起動を待機中..." -ForegroundColor Yellow
$maxRetry = 30
for ($i = 1; $i -le $maxRetry; $i++) {
    try {
        $health = Invoke-RestMethod -Uri "http://${API_HOST}:${API_PORT}/health" -ErrorAction Stop
        Write-Host "✓ APIサーバー正常起動" -ForegroundColor Green
        break
    } catch {
        Start-Sleep -Seconds 1
        if ($i -eq $maxRetry) {
            Write-Host "エラー: APIサーバーの起動がタイムアウトしました" -ForegroundColor Red
            Cleanup
            exit 1
        }
    }
}

Write-Host ""

# Streamlit起動
Write-Host "Streamlitを起動中... (port ${STREAMLIT_PORT})" -ForegroundColor Yellow
$script:streamlitProcess = Start-Process -FilePath "uv" -ArgumentList "run", "streamlit", "run", "src/frontend/signage_app.py", "--server.port", $STREAMLIT_PORT, "--server.headless", "true" -PassThru -NoNewWindow
Write-Host "✓ Streamlit起動 (PID: $($script:streamlitProcess.Id))" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "起動完了!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  API:       http://${API_HOST}:${API_PORT}"
Write-Host "  Frontend:  http://localhost:${STREAMLIT_PORT}"
Write-Host ""
Write-Host "Ctrl+C で終了" -ForegroundColor Yellow
Write-Host ""

# プロセスを監視
try {
    while ($true) {
        if ($script:apiProcess.HasExited) {
            Write-Host "APIサーバーが停止しました" -ForegroundColor Red
            break
        }
        if ($script:streamlitProcess.HasExited) {
            Write-Host "Streamlitが停止しました" -ForegroundColor Red
            break
        }
        Start-Sleep -Seconds 1
    }
} finally {
    Cleanup
}
