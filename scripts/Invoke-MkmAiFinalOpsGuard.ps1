param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"

$guard = Join-Path $WorkspaceRoot "scripts\check_mkm_ai_final_ops_guard.py"
if (-not (Test-Path -LiteralPath $guard)) {
    throw "Guard script not found: $guard"
}

& py $guard --workspace-root $WorkspaceRoot --min-pass-rate 95 --min-sample-count 3
$exitCode = $LASTEXITCODE

$reportDir = Join-Path $WorkspaceRoot "reports"
if (-not (Test-Path -LiteralPath $reportDir)) {
    New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
}

$logPath = Join-Path $reportDir "mkm_ai_final_ops_guard_log.jsonl"
$row = [ordered]@{
    schema         = "mkm_ai_final_ops_guard_log_v1"
    ts_utc         = (Get-Date).ToUniversalTime().ToString("o")
    workspace_root = $WorkspaceRoot
    exit_code      = $exitCode
}
($row | ConvertTo-Json -Compress) | Add-Content -LiteralPath $logPath -Encoding UTF8

if ($exitCode -ne 0) {
    exit $exitCode
}

exit 0
