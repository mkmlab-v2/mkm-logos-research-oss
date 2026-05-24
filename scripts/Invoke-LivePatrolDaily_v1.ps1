#Requires -Version 5.1
<#
.SYNOPSIS
  ACTIVE_MODE 일일 파수: 가벼운 병렬 + 24h 하드라인 체크리스트 JSON.
  SSOT: docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md §24h 보수 운영 하드라인
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$VpsHost = "vps-mkmlife",
    [string]$Pm2App = "bitcoin-live-small-24h"
)

$ErrorActionPreference = "Continue"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Test-Path "$env:WINDIR\py.exe") { "$env:WINDIR\py.exe" } else { "py" }

$hardline = @(
    "max_drawdown <= -3.0% (intraday)",
    "consecutive_losses >= 4",
    "slippage > 2x expected x5 consecutive",
    "order_ack_p95 > 1500ms for 10min",
    "exchange_fail_rate > 5% for 5min",
    "position/order/signal state_mismatch >= 1",
    "lens_mismatch vs price engine 3 ticks"
)

$jobs = @(
    @{ Name = "op5_verify"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify_jema12_studio_oracle_redirect_v1.ps1; exit $LASTEXITCODE } },
    @{ Name = "api_health"; Script = { param($R); Set-Location $R; $h = & curl.exe -sS https://api.no1kmedi.com/health 2>&1 | Out-String; Write-Output $h.Trim(); if ($h -notmatch '"ok"\s*:\s*true') { exit 2 }; exit 0 } },
    @{ Name = "live_sync"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-LiveSyncHeartbeatPull.ps1 -SoftFail; exit $LASTEXITCODE } },
    @{ Name = "safe_ops"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-SafeOpsSurfaceCheck.ps1 -AllowDisabledSecurityIntegrityTask; exit $LASTEXITCODE } },
    @{ Name = "vps_go"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-VpsTradingGoReadinessSync_v1.ps1; exit $LASTEXITCODE } },
    @{ Name = "vps_pm2_patrol"; Script = {
        param($R, $Vps, $App)
        Set-Location $R
        $cmd = @"
pm2 jlist 2>/dev/null | head -c 4000 || true
echo '---DESCRIBE---'
pm2 describe $App 2>/dev/null | head -22
echo '---OUT---'
tail -n 12 /root/.pm2/logs/${App}-out.log 2>/dev/null || true
echo '---ERR---'
tail -n 8 /root/.pm2/logs/${App}-error.log 2>/dev/null || true
echo '---GREP_ERR---'
grep -iE 'error|exception|traceback|failed' /root/.pm2/logs/${App}-error.log 2>/dev/null | tail -3 || true
"@
        ssh $Vps $cmd
        exit $LASTEXITCODE
    } }
)

$failed = @()
$handles = @()
foreach ($j in $jobs) {
    Write-Host "Start: $($j.Name)" -ForegroundColor Cyan
    if ($j.Name -eq "vps_pm2_patrol") {
        $handles += Start-Job -Name $j.Name -ScriptBlock $j.Script -ArgumentList $WorkspaceRoot, $VpsHost, $Pm2App
    } else {
        $handles += Start-Job -Name $j.Name -ScriptBlock $j.Script -ArgumentList $WorkspaceRoot
    }
}
$null = Wait-Job $handles
foreach ($h in $handles) {
    $out = Receive-Job $h -ErrorAction SilentlyContinue
    if ($h.State -ne "Completed") { $failed += $h.Name }
    Write-Host "--- $($h.Name) $($h.State) ---" -ForegroundColor $(if ($h.State -eq "Completed") { "Green" } else { "Yellow" })
    if ($out) { @($out)[-4..-1] | Where-Object { $_ } | ForEach-Object { Write-Host $_ } }
    Remove-Job $h -Force
}

function Read-J([string]$p) {
    if (-not (Test-Path $p)) { return $null }
    return Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json
}

$op5 = Read-J (Join-Path $WorkspaceRoot "reports\jema12_studio_oracle_redirect_check_latest.json")
$go = Read-J (Join-Path $WorkspaceRoot "docs\final\artifacts\trading_go_no_go_latest.json")
$safe = Read-J (Join-Path $WorkspaceRoot "reports\safe_ops_surface_check_latest.json")
$hb = Read-J (Join-Path $WorkspaceRoot "reports\live_sync_heartbeat_check_latest.json")
$signal = Read-J (Join-Path $WorkspaceRoot "docs\final\artifacts\track_a_signal_light_report_latest.json")

$rollup = [ordered]@{
    schema = "live_patrol_daily_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    mode = "ACTIVE_MODE_patrol"
    failed_jobs = @($failed)
    pm2_app = $Pm2App
    op5_pass = $op5.op5_pass
    op5_status = if ($op5.op5_pass) { "CLOSED_verify_only" } else { "ACTION_verify_failed" }
    go_no_go = $go.go_no_go
    risk_mode = $go.risk_mode
    safe_ops_ok = ($safe.overall_safe -eq $true)
    live_sync_status = $hb.status
    track_a_signal = $signal.overall_signal
    hardline_manual_checks = $hardline
    hardline_ssot = "docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md"
    weekly_full_sweep = "scripts/Invoke-PostG12Parallel_v1.ps1"
    guardrails = @(
        "MS_47.5pct_only_no_57.3_merge",
        "no_auto_promote_from_wf_soft",
        "pm2_restart_single_app_only"
    )
}
$outPath = Join-Path $WorkspaceRoot "reports\live_patrol_daily_latest.json"
$rollup | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $outPath -Encoding UTF8
Write-Host "WROTE: $outPath op5=$($rollup.op5_pass) go=$($rollup.go_no_go) safe=$($rollup.safe_ops_ok)" -ForegroundColor Cyan
if ($failed.Count -gt 0) { exit 1 }
if (-not $rollup.op5_pass) { exit 2 }
exit 0
