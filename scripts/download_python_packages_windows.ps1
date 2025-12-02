# Raspberry Pi Python オフラインインストールパッケージ ダウンロードスクリプト (Windows PowerShell版)
# ⚠️ 警告: このスクリプトはRaspberry Pi実機でのパッケージ取得を推奨します
#
# 理由: WSL (x86_64) でダウンロードしたパッケージは
#       Raspberry Pi (ARM64) では通常動作しません
#
# 推奨方法:
#   1. このスクリプトをRaspberry Piに転送
#   2. Raspberry Piで直接実行: ./download_python_packages.sh
#   3. 生成された.tar.gzをオフライン環境に転送
#
# 代替方法 (非推奨):
#   環境変数 $env:FORCE_ARM64=1 を設定して実行
#   $env:FORCE_ARM64=1; .\download_python_packages_windows.ps1
#
# 使い方:
#   1. PowerShellでこのスクリプトを実行
#   2. .\download_python_packages_windows.ps1
#   3. WSL内でLinuxスクリプトが実行され、パッケージがダウンロードされます

param(
    [string]$WSLDistro = "Ubuntu"
)

Write-Host "========================================" -ForegroundColor Green
Write-Host "Pythonパッケージダウンローダー (Windows版)" -ForegroundColor Green
Write-Host "WSL経由でDebian/Ubuntuパッケージをダウンロード" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# WSL確認
Write-Host "[1/5] WSL環境チェック" -ForegroundColor Green
if (-not (Get-Command wsl -ErrorAction SilentlyContinue)) {
    Write-Host "エラー: WSLがインストールされていません" -ForegroundColor Red
    Write-Host "WSLインストール方法:" -ForegroundColor Yellow
    Write-Host "  1. 管理者権限でPowerShellを開く" -ForegroundColor Yellow
    Write-Host "  2. wsl --install を実行" -ForegroundColor Yellow
    Write-Host "  3. PCを再起動" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ WSLが見つかりました" -ForegroundColor Green

# WSLディストリビューション確認
Write-Host ""
Write-Host "[2/5] WSLディストリビューション確認" -ForegroundColor Green
$wslList = wsl --list --quiet
if ($wslList -notcontains $WSLDistro) {
    Write-Host "警告: ${WSLDistro}が見つかりません" -ForegroundColor Yellow
    Write-Host "利用可能なディストリビューション:" -ForegroundColor Yellow
    wsl --list
    Write-Host ""
    $defaultDistro = (wsl --list | Select-Object -First 1).Trim()
    Write-Host "デフォルトのディストリビューション(${defaultDistro})を使用します" -ForegroundColor Yellow
    $WSLDistro = ""  # デフォルト使用
}

# スクリプトディレクトリ取得
$scriptDir = $PSScriptRoot
$linuxScriptPath = Join-Path $scriptDir "download_python_packages.sh"

# Linuxスクリプト存在チェック
Write-Host ""
Write-Host "[3/5] Linuxスクリプト確認" -ForegroundColor Green
if (-not (Test-Path $linuxScriptPath)) {
    Write-Host "エラー: download_python_packages.sh が見つかりません" -ForegroundColor Red
    Write-Host "パス: $linuxScriptPath" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Linuxスクリプトが見つかりました" -ForegroundColor Green

# WSL用パス変換 (C:\Users\... → /mnt/c/Users/...)
$wslWorkDir = $scriptDir -replace '\\', '/' -replace '^([A-Z]):', { '/mnt/' + $_.Groups[1].Value.ToLower() }

Write-Host "WSL作業ディレクトリ: $wslWorkDir" -ForegroundColor Cyan

# FORCE_ARM64モード確認
if ($env:FORCE_ARM64 -eq "1") {
    Write-Host ""
    Write-Host "⚠️ FORCE_ARM64モードが有効です" -ForegroundColor Yellow
    Write-Host "警告: クロスアーキテクチャパッケージ取得を試みます" -ForegroundColor Yellow
    Write-Host "依存関係の解決が不完全な可能性があります" -ForegroundColor Yellow
    Write-Host ""
    $forceArm64Flag = "FORCE_ARM64=1"
} else {
    $forceArm64Flag = ""
}

# WSL内でスクリプト実行
Write-Host ""
Write-Host "[4/5] WSL内でダウンロードスクリプト実行" -ForegroundColor Green
Write-Host "このプロセスには数分かかる場合があります..." -ForegroundColor Yellow
Write-Host ""

# 実行権限付与 + スクリプト実行
$wslCommand = "cd '$wslWorkDir' && chmod +x download_python_packages.sh && $forceArm64Flag ./download_python_packages.sh"

if ($WSLDistro) {
    wsl -d $WSLDistro -e bash -c $wslCommand
} else {
    wsl -e bash -c $wslCommand
}

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "エラー: WSL内でのスクリプト実行に失敗しました" -ForegroundColor Red
    Write-Host "終了コード: $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

# 生成ファイル確認
Write-Host ""
Write-Host "[5/5] 生成ファイル確認" -ForegroundColor Green

$archivePath = Join-Path $scriptDir "python_packages.tar.gz"
$packageDir = Join-Path $scriptDir "python_packages"

if (Test-Path $archivePath) {
    $archiveSize = (Get-Item $archivePath).Length / 1MB
    Write-Host "✓ アーカイブ生成成功: python_packages.tar.gz ($([math]::Round($archiveSize, 2)) MB)" -ForegroundColor Green
} else {
    Write-Host "警告: アーカイブファイルが見つかりません" -ForegroundColor Yellow
}

if (Test-Path $packageDir) {
    $dirSize = (Get-ChildItem $packageDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Host "✓ パッケージディレクトリ: python_packages/ ($([math]::Round($dirSize, 2)) MB)" -ForegroundColor Green
} else {
    Write-Host "警告: パッケージディレクトリが見つかりません" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✓ ダウンロード完了" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "⚠️ 重要な注意:" -ForegroundColor Yellow
Write-Host "  WSL(x86_64)でダウンロードしたパッケージは" -ForegroundColor White
Write-Host "  Raspberry Pi(ARM64)では動作しない可能性が高いです！" -ForegroundColor Red
Write-Host ""
Write-Host "推奨方法:" -ForegroundColor Yellow
Write-Host "  1. このスクリプトをRaspberry Piに転送" -ForegroundColor White
Write-Host "  2. Raspberry Piで直接実行:" -ForegroundColor White
Write-Host "     ./download_python_packages.sh" -ForegroundColor Cyan
Write-Host "  3. 生成されたpython_packages.tar.gzをオフライン環境に転送" -ForegroundColor White
Write-Host ""
Write-Host "生成ファイル場所:" -ForegroundColor Yellow
Write-Host "  $scriptDir" -ForegroundColor White
