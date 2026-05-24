#Requires -Version 5.1
<#
.SYNOPSIS
  G12+PM2 이후 병렬: 라이브 모니터 + 융합 핵심(Oracle/상용 제외 선택).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$VpsHost = "vps-mkmlife",
    [switch]$IncludeOracleOmni
)

$ErrorActionPreference = "Continue"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Test-Path "$env:WINDIR\py.exe") { "$env:WINDIR\py.exe" } else { "py" }

$jobs = @(
    @{ Name = "api_dns_health"; Script = { param($R,$Py); Set-Location $R; & $Py scripts/ensure_no1kmedi_api_cloudflare_dns_v1.py; if ($LASTEXITCODE -ne 0){exit 1}; $h=& curl.exe -sS https://api.no1kmedi.com/health 2>&1|Out-String; if ($h -notmatch '"ok"\s*:\s*true'){exit 2}; exit 0 } },
    @{ Name = "cf_autoverify"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-JemaaiShowroomEdgeAutoverify_v1.ps1; exit $LASTEXITCODE } },
    @{ Name = "live_sync_pull"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-LiveSyncHeartbeatPull.ps1 -SoftFail; exit $LASTEXITCODE } },
    @{ Name = "safe_ops"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-SafeOpsSurfaceCheck.ps1 -AllowDisabledSecurityIntegrityTask; exit $LASTEXITCODE } },
    @{ Name = "trading_health"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Verify-TradingAutomationHealth.ps1 -AllowPolicyLockedGoNoGo -AllowDisabledSecurityIntegrityTask; exit $LASTEXITCODE } },
    @{ Name = "vps_go_sync"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-VpsTradingGoReadinessSync_v1.ps1; exit $LASTEXITCODE } },
    @{ Name = "prophecy_closure"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ProphecyLaneRecommendedClosureBundle_v1.ps1; exit $LASTEXITCODE } },
    @{ Name = "track_a_daily"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_track_a_commercialization_daily_chain.ps1; exit $LASTEXITCODE } },
    @{ Name = "compression"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_compression_automation_chain.ps1; exit $LASTEXITCODE } },
    @{ Name = "showroom_health"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona ShowroomTrackCHealth; exit $LASTEXITCODE } },
    @{ Name = "vps_pm2_probe"; Script = {
        param($R, $VpsHostName)
        Set-Location $R
        $cmd = @"
pm2 describe bitcoin-live-small-24h 2>/dev/null | head -18
echo '---LOG---'
tail -n 8 /root/.pm2/logs/bitcoin-live-small-24h-out.log 2>/dev/null || true
echo '---ERR---'
tail -n 5 /root/.pm2/logs/bitcoin-live-small-24h-error.log 2>/dev/null || true
"@
        ssh $VpsHostName $cmd
        exit $LASTEXITCODE
    } }
)

if ($IncludeOracleOmni) {
    $jobs += @{ Name = "oracle_omni"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-LogosOracleOmniParallel_v1.ps1 -MirrorShowroomCdim; exit $LASTEXITCODE } }
}

$failed = @()
$handles = @()
foreach ($j in $jobs) {
    Write-Host "Start: $($j.Name)" -ForegroundColor Cyan
    if ($j.Name -eq "vps_pm2_probe") {
        $handles += Start-Job -Name $j.Name -ScriptBlock $j.Script -ArgumentList $WorkspaceRoot, $VpsHost
    } else {
        $handles += Start-Job -Name $j.Name -ScriptBlock $j.Script -ArgumentList $WorkspaceRoot, $py
    }
}
$null = Wait-Job $handles
foreach ($h in $handles) {
    $out = Receive-Job $h -ErrorAction SilentlyContinue
    if ($h.State -ne "Completed") { $failed += $h.Name }
    Write-Host "--- $($h.Name) $($h.State) ---" -ForegroundColor $(if ($h.State -eq "Completed"){"Green"}else{"Yellow"})
    if ($out) { @($out)[-5..-1] | Where-Object { $_ } | ForEach-Object { Write-Host $_ } }
    Remove-Job $h -Force
}

Write-Host "`n==> Serial tail" -ForegroundColor Cyan
& $py scripts/build_mkm_trackc_ops_dashboard_v1.py
& $py scripts/check_showroom_trust_viz_public_chain_v1.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-AmsaengEosaMonitoringBundleTask.ps1 -GovernanceSoftFail | Out-Null

function Read-J([string]$p) {
    if (-not (Test-Path $p)) { return $null }
    return Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json
}
$rollup = [ordered]@{
    schema = "post_g12_parallel_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    failed_jobs = @($failed)
    live_pm2_app = "bitcoin-live-small-24h"
    closure_ok = (Read-J (Join-Path $WorkspaceRoot "reports\prophecy_lane_closure_bundle_v1_latest.json")).closure_ok
    go_no_go = (Read-J (Join-Path $WorkspaceRoot "docs\final\artifacts\trading_go_no_go_latest.json")).go_no_go
    risk_mode = (Read-J (Join-Path $WorkspaceRoot "docs\final\artifacts\trading_go_no_go_latest.json")).risk_mode
    vps_aligned = (Read-J (Join-Path $WorkspaceRoot "reports\vps_trading_go_readiness_sync_latest.json")).aligned
}
$outPath = Join-Path $WorkspaceRoot "reports\post_g12_parallel_latest.json"
$rollup | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $outPath -Encoding UTF8
Write-Host "WROTE: $outPath go=$($rollup.go_no_go) risk=$($rollup.risk_mode) closure=$($rollup.closure_ok)" -ForegroundColor Cyan
if ($failed.Count -gt 0) { exit 1 }
exit 0
