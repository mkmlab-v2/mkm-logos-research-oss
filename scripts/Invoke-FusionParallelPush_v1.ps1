#Requires -Version 5.1
<#
.SYNOPSIS
  융합 병렬 밀기: 핸드오프 원클릭 + Oracle + G12 prep + 상용 (실매매 ON 없음).
#>
param([string]$WorkspaceRoot = "C:\workspace")

$ErrorActionPreference = "Continue"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Test-Path "$env:WINDIR\py.exe") { "$env:WINDIR\py.exe" } else { "py" }

$jobs = @(
    @{ Name = "api_dns_health"; Script = { param($R,$Py); Set-Location $R; & $Py scripts/ensure_no1kmedi_api_cloudflare_dns_v1.py; if ($LASTEXITCODE -ne 0){exit 1}; $h=& curl.exe -sS https://api.no1kmedi.com/health 2>&1|Out-String; Write-Output $h.Trim(); if ($h -notmatch '"ok"\s*:\s*true'){exit 2}; exit 0 } },
    @{ Name = "cf_autoverify"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-JemaaiShowroomEdgeAutoverify_v1.ps1; exit $LASTEXITCODE } },
    @{ Name = "cf_token_roles_triage"; Script = { param($R,$Py); Set-Location $R; $s=Join-Path $R "scripts\check_cloudflare_token_roles_v1.py"; if (-not (Test-Path $s)){exit 0}; & $Py $s; if ($LASTEXITCODE -eq 2) { exit 0 }; exit $LASTEXITCODE } },
    @{ Name = "athena_bundle"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona AthenaBundle; exit $LASTEXITCODE } },
    @{ Name = "showroom_health"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona ShowroomTrackCHealth; exit $LASTEXITCODE } },
    @{ Name = "prophecy_closure"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ProphecyLaneRecommendedClosureBundle_v1.ps1; exit $LASTEXITCODE } },
    @{ Name = "trackc_macro_fusion"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-TrackCMacroDailyFusion_v1.ps1 -SkipGateAlert -SkipExodusSourceFetch; exit $LASTEXITCODE } },
    @{ Name = "trackc_b2b"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-TrackCB2bMeetingPack_v1.ps1; exit $LASTEXITCODE } },
    @{ Name = "oracle_omni"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-LogosOracleOmniParallel_v1.ps1 -MirrorShowroomCdim; exit $LASTEXITCODE } },
    @{ Name = "chronology_bundle"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-LogosChronologyParallelBundle_v1.ps1 -SkipEraBlindEval; exit $LASTEXITCODE } },
    @{ Name = "premium_queue"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-PremiumMultilensQueueRoutine_v1.ps1; exit $LASTEXITCODE } },
    @{ Name = "track_a_daily"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_track_a_commercialization_daily_chain.ps1; exit $LASTEXITCODE } },
    @{ Name = "compression"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_compression_automation_chain.ps1; exit $LASTEXITCODE } },
    @{ Name = "g12_prep"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-G12PrepParallel_v1.ps1; exit $LASTEXITCODE } },
    @{ Name = "showroom_publish"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ShowroomTrackCPublishRoutine_v1.ps1; exit $LASTEXITCODE } },
    @{ Name = "p0_paths"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify_p0_constitution_gate_paths.ps1; exit $LASTEXITCODE } }
)

$results = @{}
$handles = @()
foreach ($j in $jobs) {
    Write-Host "Start: $($j.Name)" -ForegroundColor Cyan
    $handles += Start-Job -Name $j.Name -ScriptBlock $j.Script -ArgumentList $WorkspaceRoot, $py
}

$failed = @()
foreach ($h in $handles) {
    $null = Wait-Job -Job $h
    $out = Receive-Job -Job $h -ErrorAction SilentlyContinue
    $ok = ($h.State -eq "Completed")
    $results[$h.Name] = $ok
    if (-not $ok) { $failed += $h.Name }
    $color = if ($ok) { "Green" } else { "Yellow" }
    Write-Host "--- $($h.Name) state=$($h.State) ---" -ForegroundColor $color
    if ($out) { @($out)[-4..-1] | Where-Object { $_ } | ForEach-Object { Write-Host $_ } }
    Remove-Job -Job $h -Force
}

Write-Host "`n==> Serial tail" -ForegroundColor Cyan
& $py scripts/build_mkm_trackc_ops_dashboard_v1.py
& $py scripts/check_showroom_trust_viz_public_chain_v1.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-AmsaengEosaMonitoringBundleTask.ps1 -GovernanceSoftFail | Out-Null

# Fusion status rollup
function Read-J([string]$p) {
    if (-not (Test-Path $p)) { return $null }
    return Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json
}
$rollup = [ordered]@{
    schema = "fusion_parallel_push_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    job_results = $results
    failed_jobs = @($failed)
    closure_ok = (Read-J (Join-Path $WorkspaceRoot "reports\prophecy_lane_closure_bundle_v1_latest.json")).closure_ok
    track_a_signal = (Read-J (Join-Path $WorkspaceRoot "docs\final\artifacts\track_a_signal_light_report_latest.json")).signal_light.status
    cf_apply_ok = (Read-J (Join-Path $WorkspaceRoot "reports\jemaai_cloud_showroom_cf_edge_apply_v1_latest.json")).ok
    g12_status = (Read-J (Join-Path $WorkspaceRoot "reports\g12_human_gate_readiness_latest.json")).g12_status
    live_trading_enabled = $false
}
$outPath = Join-Path $WorkspaceRoot "reports\fusion_parallel_push_latest.json"
$rollup | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $outPath -Encoding UTF8
Write-Host "WROTE: $outPath closure=$($rollup.closure_ok) track_a=$($rollup.track_a_signal) cf=$($rollup.cf_apply_ok) g12=$($rollup.g12_status)" -ForegroundColor Cyan

if ($failed.Count -gt 0) {
    Write-Host "Non-completed: $($failed -join ', ')" -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Fusion parallel push complete" -ForegroundColor Green
exit 0
