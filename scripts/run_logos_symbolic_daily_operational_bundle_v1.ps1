# Logos symbolic daily operational bundle (B-track candidate maintenance).
# Runs a stable one-shot chain with recommended defaults:
# - external ingest (+ as-of clamp)
# - blind split
# - promotion gate (non-synthetic >= 20)
# - human review queue refresh
# - hygiene audit
# - source performance breakdown
# - rolling-window revalidation report
#
# Usage:
#   pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/run_logos_symbolic_daily_operational_bundle_v1.ps1
#
param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$InstrumentId = "KOSPI",
  [string]$Horizon = "1d",
  [int]$MinHoldoutSamples = 10,
  [double]$MinHoldoutHitRate = 0.5,
  [int]$MinNonSyntheticSamples = 20,
  [double]$AuditMaxHitRateDrop = 0.05,
  [int]$AuditMaxNonSyntheticDrop = 2
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

$dailyChain = Join-Path $WorkspaceRoot "scripts\run_btrack_daily_hypothesis_chain.ps1"
if (-not (Test-Path -LiteralPath $dailyChain)) {
  throw "Missing chain script: $dailyChain"
}

Write-Host "==> run_btrack_daily_hypothesis_chain.ps1 (logos daily operational bundle)"
pwsh -NoProfile -ExecutionPolicy Bypass -File $dailyChain `
  -IncludeLogosSymbolicPromotionChain `
  -EnableLogosSymbolicExternalFeedIngest `
  -EnableLogosExternalFeedAsOfClamp `
  -EnableLogosSymbolicBlindSplit `
  -EnableLogosSymbolicHumanReviewQueue `
  -EnableLogosSymbolicDataHygieneAudit `
  -EnableLogosSymbolicRevalidationReport `
  -LogosSymbolicInstrumentId $InstrumentId `
  -LogosSymbolicHorizon $Horizon `
  -LogosMinHoldoutSamples $MinHoldoutSamples `
  -LogosMinHoldoutHitRate $MinHoldoutHitRate `
  -LogosMinNonSyntheticSamples $MinNonSyntheticSamples `
  -LogosAuditMaxHitRateDrop $AuditMaxHitRateDrop `
  -LogosAuditMaxNonSyntheticDrop $AuditMaxNonSyntheticDrop

if ($LASTEXITCODE -ne 0) {
  throw "run_btrack_daily_hypothesis_chain.ps1 exit $LASTEXITCODE"
}

$breakdownScript = Join-Path $WorkspaceRoot "scripts\build_logos_symbolic_source_performance_breakdown_v1.py"
if (-not (Test-Path -LiteralPath $breakdownScript)) {
  throw "Missing source breakdown script: $breakdownScript"
}

Write-Host "==> build_logos_symbolic_source_performance_breakdown_v1.py"
py $breakdownScript `
  --backtest-json "docs\final\artifacts\logos_symbolic_event_backtest_latest.json" `
  --output-json "docs\final\artifacts\logos_symbolic_source_performance_breakdown_latest.json"
if ($LASTEXITCODE -ne 0) {
  throw "build_logos_symbolic_source_performance_breakdown_v1.py exit $LASTEXITCODE"
}

Write-Host "OK: Logos symbolic daily operational bundle finished."
