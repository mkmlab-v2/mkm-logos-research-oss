# Single local 24h daemon recycle: fee-guard cap on disk + new code loads risk profile (no PM2).
# Does NOT: prophecy live enable, headline promote, disable trading globally.
param(
    [int]$WaitSeconds = 25,
    [int]$MaxTradesPerDay = 6
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$projectRoot = Join-Path $WorkspaceRoot "projects\bitcoin-trading"
$ensureScript = Join-Path $projectRoot "ops\windows-rehearsal\ensure_daemon_running.ps1"
$reportPath = Join-Path $WorkspaceRoot "reports\local_live_daemon_fee_guard_restart_v1_latest.json"

Set-Location -LiteralPath $WorkspaceRoot

[Environment]::SetEnvironmentVariable("MKM_FEE_GUARD_MAX_TRADES_PER_DAY", [string]$MaxTradesPerDay, "User")
[Environment]::SetEnvironmentVariable("MKM_FEE_GUARD_MAX_TRADES_PER_DAY", [string]$MaxTradesPerDay, "Process")

Write-Host "==> fee guard (max_trades=$MaxTradesPerDay)" -ForegroundColor Cyan
py scripts/apply_live_fee_guard_recommended_posture_v1.py --max-trades-per-day $MaxTradesPerDay
if ($LASTEXITCODE -ne 0) { throw "fee_guard exit $LASTEXITCODE" }

Write-Host "==> stop existing start_24h_daemon (single recycle)" -ForegroundColor Cyan
Get-CimInstance Win32_Process |
    Where-Object {
        $_.CommandLine -and
        ($_.CommandLine -match 'start_24h_daemon\.py') -and
        ($_.Name -notin @('py.exe', 'cmd.exe'))
    } |
    ForEach-Object {
        Write-Host "  stop PID=$($_.ProcessId)"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
Start-Sleep -Seconds 3

Write-Host "==> ensure_daemon_running (sync + fee guard + start)" -ForegroundColor Cyan
& $ensureScript
if ($LASTEXITCODE -ne 0) { throw "ensure_daemon exit $LASTEXITCODE" }

Write-Host "==> wait ${WaitSeconds}s for heartbeat" -ForegroundColor Cyan
Start-Sleep -Seconds $WaitSeconds

$hbPath = Join-Path $projectRoot "memory\trading_daemon_heartbeat.txt"
$riskPath = Join-Path $projectRoot "memory\v2\risk\risk_profile_fact_safe_latest.json"
$healthScript = Join-Path $projectRoot "ops\windows-rehearsal\check_live_trading_health.ps1"
$hbAge = $null
$hbFresh = $false
if (Test-Path -LiteralPath $hbPath) {
    $hb = [datetime]::Parse((Get-Content -LiteralPath $hbPath -Raw).Trim())
    $hbAge = ((Get-Date) - $hb).TotalMinutes
    $hbFresh = $hbAge -lt 5
}

$risk = $null
if (Test-Path -LiteralPath $riskPath) {
    $risk = Get-Content -LiteralPath $riskPath -Raw | ConvertFrom-Json
}

$healthExit = $null
if (Test-Path -LiteralPath $healthScript) {
    & $healthScript
    $healthExit = $LASTEXITCODE
}

$procs = @(Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -and $_.CommandLine -match 'start_24h_daemon\.py' -and ($_.Name -notin @('py.exe', 'cmd.exe')) })

$report = [ordered]@{
    schema = "local_live_daemon_fee_guard_restart_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    max_trades_per_day_target = $MaxTradesPerDay
    disk_max_trades_per_day = $risk.max_trades_per_day
    maker_only_level = $risk.maker_only_level
    daemon_process_count = $procs.Count
    heartbeat_fresh_under_5m = $hbFresh
    heartbeat_age_minutes = $hbAge
    live_health_exit = $healthExit
    prophecy_routing_changed = $false
    operator_note = "Local recycle only; hot-reload + fee cap on disk. Watch next 24h trade_count vs cap."
}
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $reportPath -Encoding utf8
Write-Host "WROTE: $reportPath" -ForegroundColor Green
$report | ConvertTo-Json -Depth 6
