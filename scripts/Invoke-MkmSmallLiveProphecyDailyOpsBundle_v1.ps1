#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot Mode B: daily prophecy chain + eval report + trading comfort check (no VPS trading changes).

.EXAMPLE
  pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-MkmSmallLiveProphecyDailyOpsBundle_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipHypothesisChain,
    [switch]$SkipEvalReport,
    [switch]$SkipTradingCheck,
    [switch]$SkipBtrackVpsSeparation,
    [switch]$SkipNeutralAttribution
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

if (-not $SkipHypothesisChain) {
    Write-Host "==> run_btrack_daily_hypothesis_chain (btc)" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\run_btrack_daily_hypothesis_chain.ps1") `
        -WorkspaceRoot $WorkspaceRoot -ResearchEvaluationInstrument btc -SkipPanel24hAlertsCheck -SkipProphecyContemplationGemini
    if ($LASTEXITCODE -ne 0) { throw "hypothesis chain exit $LASTEXITCODE" }
}

if (-not $SkipEvalReport) {
    Write-Host "==> run_daily_prophecy_eval_and_report" -ForegroundColor Cyan
    $btcCsv = Join-Path $WorkspaceRoot "research\market_data\btc_daily_external_yf.csv"
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\run_daily_prophecy_eval_and_report.ps1") `
        -WorkspaceRoot $WorkspaceRoot -RecentTradingDays 7 -SkipTrinityEvolution -BtcCsvPath $btcCsv
    if ($LASTEXITCODE -ne 0) { throw "eval report exit $LASTEXITCODE" }
}

if (-not $SkipTradingCheck) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Invoke-MkmDailyShowroomTradingCheck_v1.ps1")
}

if (-not $SkipBtrackVpsSeparation) {
    Write-Host "==> build_btrack_vps_pnl_separation_report_v1" -ForegroundColor Cyan
    & py (Join-Path $WorkspaceRoot "scripts\build_btrack_vps_pnl_separation_report_v1.py")
    if ($LASTEXITCODE -ne 0) { throw "btrack vps pnl separation exit $LASTEXITCODE" }
}

if (-not $SkipNeutralAttribution) {
    Write-Host "==> analyze_btrack_neutral_attribution_v1" -ForegroundColor Cyan
    & py (Join-Path $WorkspaceRoot "scripts\analyze_btrack_neutral_attribution_v1.py")
    if ($LASTEXITCODE -ne 0) { throw "neutral attribution exit $LASTEXITCODE" }
}

Write-Host "[OK] Mode B bundle complete" -ForegroundColor Green
