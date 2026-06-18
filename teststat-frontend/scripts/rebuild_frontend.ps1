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
    Write-Host "`n[1/3] pnpm install..." -ForegroundColor Yellow
    pnpm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "pnpm install failed." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "`n[1/3] node_modules あり - install スキップ" -ForegroundColor DarkGray
}

# ビルド
Write-Host "`n[2/3] pnpm run build..." -ForegroundColor Yellow
pnpm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed." -ForegroundColor Red
    exit 1
}

# web.config 生成
Write-Host "`n[3/3] web.config を生成..." -ForegroundColor Yellow

$backendUrl = "http://127.0.0.1:18000"
$envFile = Join-Path $frontendDir ".env"
if (Test-Path $envFile) {
    $line = Get-Content $envFile | Where-Object { $_ -match "^VITE_BACKEND_URL\s*=" } | Select-Object -First 1
    if ($line) {
        $backendUrl = ($line -split "=", 2)[1].Trim()
    }
}

$webConfig = @"
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <rewrite>
      <rules>
        <rule name="API Proxy" stopProcessing="true">
          <match url="^api/(.*)" />
          <action type="Rewrite" url="$backendUrl/api/{R:1}" />
        </rule>
        <rule name="Health Proxy" stopProcessing="true">
          <match url="^health`$" />
          <action type="Rewrite" url="$backendUrl/health" />
        </rule>
        <rule name="SPA Fallback" stopProcessing="true">
          <match url=".*" />
          <conditions>
            <add input="{REQUEST_FILENAME}" matchType="IsFile" negate="true" />
            <add input="{REQUEST_FILENAME}" matchType="IsDirectory" negate="true" />
          </conditions>
          <action type="Rewrite" url="index.html" />
        </rule>
      </rules>
    </rewrite>
  </system.webServer>
</configuration>
"@

$webConfig | Set-Content -Path "dist\web.config" -Encoding UTF8
Write-Host "dist\web.config を生成しました。(backend: $backendUrl)" -ForegroundColor Green

Write-Host "`nBuild succeeded. -> dist/" -ForegroundColor Green
