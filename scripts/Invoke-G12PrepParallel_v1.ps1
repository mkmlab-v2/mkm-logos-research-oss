#Requires -Version 5.1
<#
.SYNOPSIS
  G12 전 단계 병렬: 증거 번들·comfort brief·preflight·클로저·Track A daily (실매매 ON 없음).
#>
param([string]$WorkspaceRoot = "C:\workspace")

$ErrorActionPreference = "Continue"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Test-Path "$env:WINDIR\py.exe") { "$env:WINDIR\py.exe" } else { "py" }

$jobs = @(
    @{ Name = "promotion_evidence"; Script = { param($R, $Py); Set-Location $R; & $Py scripts/build_mkm_promotion_gate_evidence_bundle_v1.py; exit $LASTEXITCODE } },
    @{ Name = "comfort_brief"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-TradingComfortReadinessBrief_v1.ps1; exit $LASTEXITCODE } },
    @{ Name = "preflight_live"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File projects\bitcoin-trading\scripts\preflight_live_trading_readiness.ps1; exit $LASTEXITCODE } },
    @{ Name = "prophecy_closure"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ProphecyLaneRecommendedClosureBundle_v1.ps1; exit $LASTEXITCODE } },
    @{ Name = "track_a_daily"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_track_a_commercialization_daily_chain.ps1; exit $LASTEXITCODE } },
    @{ Name = "compression"; Script = { param($R); Set-Location $R; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_compression_automation_chain.ps1; exit $LASTEXITCODE } },
    @{ Name = "vps_trading_readiness"; Script = { param($R); Set-Location $R; $p = Join-Path $R "scripts\Invoke-VpsTradingGoReadinessSync_v1.ps1"; if (-not (Test-Path $p)) { exit 0 }; powershell -NoProfile -ExecutionPolicy Bypass -File $p; exit $LASTEXITCODE } }
)

$failed = @()
foreach ($j in $jobs) {
    Write-Host "Start: $($j.Name)" -ForegroundColor Cyan
    $h = Start-Job -Name $j.Name -ScriptBlock $j.Script -ArgumentList $WorkspaceRoot, $py
    $null = Wait-Job $h
    $out = Receive-Job $h -ErrorAction SilentlyContinue
    if ($out) { @($out)[-6..-1] | Where-Object { $_ } | ForEach-Object { Write-Host $_ } }
    if ($h.State -ne "Completed") { $failed += $j.Name; Write-Host "FAIL: $($j.Name)" -ForegroundColor Red }
    else { Write-Host "OK: $($j.Name)" -ForegroundColor Green }
    Remove-Job $h -Force
}

# G12 readiness rollup (no live enable)
$bundle = Join-Path $WorkspaceRoot "docs\final\artifacts\mkm_promotion_gate_evidence_bundle_v1.json"
$closure = Join-Path $WorkspaceRoot "reports\prophecy_lane_closure_bundle_v1_latest.json"
$signal = Join-Path $WorkspaceRoot "docs\final\artifacts\track_a_signal_light_report_latest.json"
$brief = Join-Path $WorkspaceRoot "reports\trading_comfort_readiness_brief_latest.json"

function Read-J([string]$p) {
    if (-not (Test-Path $p)) { return $null }
    return Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json
}

$ev = Read-J $bundle
$cl = Read-J $closure
$sg = Read-J $signal
$br = Read-J $brief

$g12 = $ev.gates.G12
$rollup = [ordered]@{
    schema = "g12_human_gate_readiness_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    g12_status = if ($g12) { $g12.status } else { "unknown" }
    g12_note = "Live trading / billing requires explicit commander message: G12 GO"
    automated_prereqs = [ordered]@{
        promotion_g0_g11 = "pass_if_evidence_bundle_gates_pass"
        prophecy_closure_ok = if ($cl) { [bool]$cl.closure_ok } else { $false }
        track_a_signal_light = if ($sg) { $sg.signal_light.status } else { "unknown" }
        trading_go_no_go = if ($br) { $br.trading_go_no_go } else { $null }
    }
    commander_action_required = "Send one line: G12 GO (then apply_prophecy_live_enable / VPS live per LOCAL_VS_VPS runbook; not run by this script)"
    failed_parallel_jobs = @($failed)
}
$outPath = Join-Path $WorkspaceRoot "reports\g12_human_gate_readiness_latest.json"
$rollup | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $outPath -Encoding UTF8
Write-Host "WROTE: $outPath g12=$($rollup.g12_status) closure=$($rollup.automated_prereqs.prophecy_closure_ok)" -ForegroundColor Cyan

if ($failed.Count -gt 0) { exit 1 }
exit 0
