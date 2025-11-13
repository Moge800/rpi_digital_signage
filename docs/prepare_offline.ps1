# オフライン環境デプロイ用パッケージダウンロードスクリプト
# Windows開発環境で実行

Write-Host "======================================"
Write-Host "  パッケージダウンロード (Linux ARM64用)"
Write-Host "======================================"

# packagesディレクトリ作成
if (!(Test-Path "packages")) {
    New-Item -ItemType Directory -Path "packages"
}

Write-Host "[1/2] Pythonパッケージをダウンロード中..."

# 方法1: pipを使用 (Python環境が必要)
# 依存パッケージをLinux ARM64用にダウンロード
python -m pip download `
    plotly `
    pydantic-settings `
    pymcprotocol `
    python-dotenv `
    streamlit `
    streamlit-autorefresh `
    --platform manylinux_2_17_aarch64 `
    --platform manylinux_2_28_aarch64 `
    --only-binary=:all: `
    --python-version 3.13 `
    --dest packages/

Write-Host "[2/2] アーカイブを作成中..."

# プロジェクトをアーカイブ (.venv等を除外)
tar -czf rpi_digital_signage.tar.gz `
    --exclude=.venv `
    --exclude=.git `
    --exclude=__pycache__ `
    --exclude=logs `
    --exclude=.mypy_cache `
    --exclude=packages `
    .

Write-Host "======================================"
Write-Host "  完了！"
Write-Host "======================================" -ForegroundColor Green
Write-Host ""
Write-Host "以下をRaspberry Piに転送してください:" -ForegroundColor Yellow
Write-Host "  - rpi_digital_signage.tar.gz"
Write-Host "  - packages/ フォルダ"
Write-Host ""
Write-Host "Raspberry Pi上での展開:" -ForegroundColor Yellow
Write-Host "  tar -xzf rpi_digital_signage.tar.gz"
Write-Host "  ./setup_rpi_offline.sh"
