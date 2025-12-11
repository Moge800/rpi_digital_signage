# Lint & Type Checkをまとめて実行
# PowerShell版

$ErrorActionPreference = "Stop"

Write-Host "🔍 Running Ruff..." -ForegroundColor Cyan
uv run ruff check src/ tests/

Write-Host "🎨 Running Black..." -ForegroundColor Cyan
uv run black --check src/ tests/

Write-Host "🧪 Running ty Check..." -ForegroundColor Cyan
uvx ty check .

Write-Host "🔎 Running mypy..." -ForegroundColor Cyan
uv run mypy src/ tests/

Write-Host "✅ All checks passed!" -ForegroundColor Green
