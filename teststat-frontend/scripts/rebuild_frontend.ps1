# teststat-frontend ビルドスクリプト
# このスクリプトは teststat-frontend ディレクトリ内、または rebuild_frontend.bat から実行する

param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $PSScriptRoot
$frontendDir = $scriptDir

Write-Host "=== teststat-frontend rebuild ===" -ForegroundColor Cyan
Write-Host "Dir: $frontendDir"

Set-Location $frontendDir

# node_modules がない、または --skip-install 未指定の場合にインストール
if (-not $SkipInstall -and -not (Test-Path "node_modules")) {
    Write-Host "`n[1/2] pnpm install..." -ForegroundColor Yellow
    pnpm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "pnpm install failed." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "`n[1/2] node_modules あり - install スキップ" -ForegroundColor DarkGray
}

# ビルド
Write-Host "`n[2/2] pnpm run build..." -ForegroundColor Yellow
pnpm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed." -ForegroundColor Red
    exit 1
}

Write-Host "`nBuild succeeded. -> dist/" -ForegroundColor Green
