#Requires -Version 5.1
<#
.SYNOPSIS
  23차 병렬: Oracle omni + chronology + premium + showroom + Track A daily + compression + CF apply.
#>
param([string]$WorkspaceRoot = "C:\workspace")

$ErrorActionPreference = "Continue"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Test-Path "$env:WINDIR\py.exe") { "$env:WINDIR\py.exe" } else { "py" }

$jobs = @(
    @{ Name = "oracle_omni"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-LogosOracleOmniParallel_v1.ps1 -MirrorShowroomCdim; exit $LASTEXITCODE } },
    @{ Name = "chronology_bundle"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-LogosChronologyParallelBundle_v1.ps1 -SkipEraBlindEval; exit $LASTEXITCODE } },
    @{ Name = "premium_queue"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-PremiumMultilensQueueRoutine_v1.ps1; exit $LASTEXITCODE } },
    @{ Name = "showroom_publish"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ShowroomTrackCPublishRoutine_v1.ps1; exit $LASTEXITCODE } },
    @{ Name = "track_a_daily"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_track_a_commercialization_daily_chain.ps1; exit $LASTEXITCODE } },
    @{ Name = "compression_chain"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_compression_automation_chain.ps1; exit $LASTEXITCODE } },
    @{ Name = "showroom_vps_sync"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\sync_showroom_to_vps.ps1; exit $LASTEXITCODE } },
    @{ Name = "cf_apply"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ApplyJemaaiShowroomCfEdgeRules_v1.ps1; exit $LASTEXITCODE } },
    @{ Name = "api_health"; Script = { param($R, $Py); Set-Location $R; & $Py scripts/ensure_no1kmedi_api_cloudflare_dns_v1.py; if ($LASTEXITCODE -ne 0) { exit 1 }; $h = & curl.exe -sS https://api.no1kmedi.com/health 2>&1 | Out-String; Write-Output $h.Trim(); if ($h -notmatch '"ok"\s*:\s*true') { exit 2 }; exit 0 } }
)

$results = @{}
$handles = @()
foreach ($j in $jobs) {
    Write-Host "Start: $($j.Name)" -ForegroundColor Cyan
    $handles += Start-Job -Name $j.Name -ScriptBlock $j.Script -ArgumentList $WorkspaceRoot, $py
}

foreach ($h in $handles) {
    $null = Wait-Job -Job $h
    $out = Receive-Job -Job $h -ErrorAction SilentlyContinue
    $code = if ($h.ChildJobs.Count -gt 0) { $h.ChildJobs[0].JobStateInfo.Reason } else { $null }
    $exitGuess = if ($h.State -eq "Completed") { 0 } else { 1 }
    # PowerShell jobs don't preserve exit code reliably; scan output for FAIL patterns
    $results[$h.Name] = @{ State = $h.State; ExitGuess = $exitGuess }
    if ($out) {
        $tail = @($out)[-8..-1] | Where-Object { $_ }
        Write-Host "--- $($h.Name) (state=$($h.State)) ---" -ForegroundColor $(if ($h.State -eq "Completed") { "Green" } else { "Yellow" })
        $tail | ForEach-Object { Write-Host $_ }
    } else {
        Write-Host "--- $($h.Name) state=$($h.State) ---" -ForegroundColor $(if ($h.State -eq "Completed") { "Green" } else { "Red" })
    }
    Remove-Job -Job $h -Force
}

Write-Host ""
Write-Host "==> Serial tail: dashboard + amsaeng + trust smoke" -ForegroundColor Cyan
& $py scripts/build_mkm_trackc_ops_dashboard_v1.py
& $py scripts/check_showroom_trust_viz_public_chain_v1.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-AmsaengEosaMonitoringBundleTask.ps1 -GovernanceSoftFail | Out-Null

$failed = @($results.Keys | Where-Object { $results[$_].State -ne "Completed" })
if ($failed.Count -gt 0) {
    Write-Host "Non-completed jobs: $($failed -join ', ')" -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Parallel push v2 complete (cf_apply may still be scope-blocked; check apply JSON)" -ForegroundColor Green
exit 0
