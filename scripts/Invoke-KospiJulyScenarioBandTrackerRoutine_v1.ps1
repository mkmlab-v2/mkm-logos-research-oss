#Requires -Version 5.1
<#
.SYNOPSIS
  P0+P1: refresh KOSPI daily flow (pykrx net buy) + rollup + July scenario band tracker [HYPO].

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-KospiJulyScenarioBandTrackerRoutine_v1.ps1

.EXAMPLE
  powershell -File scripts\Invoke-KospiJulyScenarioBandTrackerRoutine_v1.ps1 -SkipFlowFetch
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$FromDate = "",
    [string]$ToDate = "",
    [switch]$SkipFlowFetch,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path -LiteralPath $WorkspaceRoot
Set-Location -LiteralPath $root

if (-not $FromDate) {
    $FromDate = (Get-Date).AddDays(-14).ToString("yyyy-MM-dd")
}
if (-not $ToDate) {
    $ToDate = (Get-Date).ToString("yyyy-MM-dd")
}

if (-not $SkipFlowFetch) {
    Write-Host "==> fetch_kospi_daily_flow_pykrx_v1.py ($FromDate .. $ToDate)"
    if ($DryRun) {
        py scripts/fetch_kospi_daily_flow_pykrx_v1.py --from-date $FromDate --to-date $ToDate --dry-run
    } else {
        py scripts/fetch_kospi_daily_flow_pykrx_v1.py --from-date $FromDate --to-date $ToDate
        if ($LASTEXITCODE -ne 0) { throw "flow fetch exit $LASTEXITCODE" }
    }
} else {
    Write-Host "SKIP flow fetch"
}

if ($DryRun) {
    Write-Host "DRY RUN complete"
    exit 0
}

Write-Host "==> Invoke-KospiDailyFlowRollupRoutine_v1.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-KospiDailyFlowRollupRoutine_v1.ps1 -WorkspaceRoot $root
if ($LASTEXITCODE -ne 0) { throw "rollup routine exit $LASTEXITCODE" }

Write-Host "==> build_kospi_july_scenario_band_tracker_v1.py"
py scripts/build_kospi_july_scenario_band_tracker_v1.py --append-log
if ($LASTEXITCODE -ne 0) { throw "tracker exit $LASTEXITCODE" }

Write-Host "OK KospiJulyScenarioBandTrackerRoutine"
