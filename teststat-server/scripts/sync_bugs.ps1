param(
    [string]$BaseUrl = ""
)

if ($env:TESTSTAT_SERVER_URL) { $BaseUrl = $env:TESTSTAT_SERVER_URL }
if (-not $BaseUrl) { $BaseUrl = "http://localhost:18000" }

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir = if ($env:SYNC_BUGS_LOG_DIR) { $env:SYNC_BUGS_LOG_DIR } else { Join-Path $scriptDir "logs" }
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$logFile = Join-Path $logDir ("sync_bugs_" + (Get-Date -Format "yyyyMMdd") + ".log")

function Log($msg) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"
    Add-Content -Path $logFile -Value $line
    Write-Host $line
}

Log "sync_bugs.ps1 start BaseUrl=$BaseUrl"

try {
    $projects = Invoke-RestMethod -Method GET -Uri "$BaseUrl/api/v1/projects" -UseBasicParsing
} catch {
    Log "プロジェクト一覧取得失敗: $($_.Exception.Message)"
    exit 1
}

$targets = @($projects | Where-Object { $_.bug_count_source -eq "azure_devops" -and -not $_.archived })
if ($targets.Count -eq 0) {
    Log "対象プロジェクトなし (bug_count_source=azure_devops のプロジェクトがありません)"
    exit 0
}

Log "対象プロジェクト $($targets.Count) 件"

$failed = 0
$authErr = 0

foreach ($p in $targets) {
    $tid  = $p.testing_id
    $name = $p.name
    try {
        $r = Invoke-RestMethod -Method POST -Uri "$BaseUrl/api/v1/projects/$tid/bugs/sync" -UseBasicParsing
        Log "testing_id=$tid ($name) 成功 fetched=$($r.fetched) open=$($r.open_count) suspended=$($r.suspended_count) resolved=$($r.resolved_count)"
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        if ($code -eq 502) {
            $authErr++
            Log "testing_id=$tid ($name) 認証エラー (502) - Azure DevOps PAT を確認してください"
        } elseif ($code -eq 503) {
            $failed++
            Log "testing_id=$tid ($name) 設定なし (503) - Azure DevOps 連携が設定されていません"
        } elseif ($code -eq 404) {
            $failed++
            Log "testing_id=$tid ($name) 親 Work Item 未検出 (404)"
        } elseif ($code -eq 409) {
            Log "testing_id=$tid ($name) アーカイブ済みのためスキップ (409)"
        } else {
            $failed++
            Log "testing_id=$tid ($name) 失敗 HTTP=$code $($_.Exception.Message)"
        }
    }
}

if ($authErr -gt 0) {
    Log "sync_bugs.ps1 end exit=2 (認証エラーあり)"
    exit 2
}
if ($failed -gt 0) {
    Log "sync_bugs.ps1 end exit=1 (失敗あり)"
    exit 1
}
Log "sync_bugs.ps1 end exit=0"
exit 0
