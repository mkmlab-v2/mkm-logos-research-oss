# One-click chain:
# raw(close html/text) -> normalized snapshot text -> market_pulse -> risk profile sync -> optional pilot smoke
#
# Examples
# 1) file:// fixture with tactical dry-run
#   pwsh -NoProfile -File scripts/Run-MarketPulseTacticalChain.ps1 `
#     -InputUrl "file:///C:/workspace/tests/fixtures/kr_market_close_snapshot_raw_20260504.html" `
#     -EnableTacticalLong `
#     -RunPilotSmoke
#
# 2) live URL and only build/sync (no pilot smoke)
#   pwsh -NoProfile -File scripts/Run-MarketPulseTacticalChain.ps1 `
#     -InputUrl "https://finance.naver.com/sise/" `
#     -SkipPilotSmoke

param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$InputPath = "",
  [string]$InputUrl = "",
  [string]$OutSnapshotText = "reports/market_close_snapshot_latest.txt",
  [string]$OutSnapshotMeta = "reports/market_close_snapshot_extract_latest.json",
  [string]$OutMarketPulse = "reports/market_pulse_latest.json",
  [string]$OutRiskJson = "projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json",
  [string]$UpdatedAtUtc = "",
  [switch]$EnableTacticalLong,
  [double]$TacticalMaxQty = 0.002,
  [double]$TacticalMinBreadthRatio = 1.05,
  [double]$TacticalMinNetBuyKrwEok = 30000.0,
  [double]$TacticalMinThemeScore = 0.70,
  [switch]$RunLoopIntervalMatrix,
  [string]$LoopIntervals = "1,4,6,12,24",
  [int]$LoopBinanceLimit = 5000,
  [string]$LoopMatrixOut = "docs/final/artifacts/btc_loop_interval_matrix_latest.json",
  [switch]$RecommendBestLoopTask,
  [switch]$ApplyBestLoopTask,
  [switch]$ApplyBestLoopTaskOnChangeOnly,
  [int]$BestLoopSkipNoChangeAlertThreshold = 3,
  [double]$BestLoopMinTestScore = 0.0,
  [double]$BestLoopMinStability = 0.9,
  [string]$BestLoopTaskName = "Bitcoin-V2-Execute-Guarded-Adaptive",
  [switch]$RunPilotSmoke,
  [switch]$SkipPilotSmoke
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

if ([string]::IsNullOrWhiteSpace($InputPath) -and [string]::IsNullOrWhiteSpace($InputUrl)) {
  throw "Provide one input: -InputPath or -InputUrl."
}
if (-not [string]::IsNullOrWhiteSpace($InputPath) -and -not [string]::IsNullOrWhiteSpace($InputUrl)) {
  throw "Use only one input source: -InputPath or -InputUrl."
}
if ($RunPilotSmoke -and $SkipPilotSmoke) {
  throw "Use either -RunPilotSmoke or -SkipPilotSmoke, not both."
}

$extract = "scripts/extract_kr_market_close_snapshot_text_v1.py"
$buildPulse = "scripts/build_market_pulse_from_close_snapshot_v1.py"
$syncRisk = "scripts/sync_fact_safe_risk_profile.py"
$loopMatrix = "scripts/evaluate_btc_loop_interval_matrix_v1.py"
$setBestLoopTask = "scripts/Set-BestLoopExecuteGuardedTask.ps1"
$pilot = "scripts/Run-BinanceUsdmPilotSmoke.ps1"

$extractArgs = @($extract, "--out-text", $OutSnapshotText, "--out-json", $OutSnapshotMeta)
if (-not [string]::IsNullOrWhiteSpace($InputPath)) {
  $extractArgs += @("--input", $InputPath)
} else {
  $extractArgs += @("--input-url", $InputUrl)
}

Write-Host "==> Extract close snapshot text" -ForegroundColor Cyan
py @extractArgs
if ($LASTEXITCODE -ne 0) { throw "extract close snapshot failed: $LASTEXITCODE" }

$pulseArgs = @($buildPulse, "--input-text", $OutSnapshotText, "--out", $OutMarketPulse)
if (-not [string]::IsNullOrWhiteSpace($UpdatedAtUtc)) {
  $pulseArgs += @("--updated-at-utc", $UpdatedAtUtc)
}
Write-Host "==> Build market pulse" -ForegroundColor Cyan
py @pulseArgs
if ($LASTEXITCODE -ne 0) { throw "build market pulse failed: $LASTEXITCODE" }

Write-Host "==> Sync Fact-Safe risk profile (repo source)" -ForegroundColor Cyan
py $syncRisk --repo-source --output $OutRiskJson --market-pulse-json $OutMarketPulse
if ($LASTEXITCODE -ne 0) { throw "sync risk profile failed: $LASTEXITCODE" }

$doLoopMatrix = $RunLoopIntervalMatrix
if ($doLoopMatrix) {
  Write-Host "==> Evaluate BTC loop interval matrix" -ForegroundColor Cyan
  py $loopMatrix --symbol BTCUSDT --binance-limit $LoopBinanceLimit --intervals $LoopIntervals --out $LoopMatrixOut
  if ($LASTEXITCODE -ne 0) { throw "loop interval matrix failed: $LASTEXITCODE" }
}

$doRecommendTask = $RecommendBestLoopTask -or $ApplyBestLoopTask
if ($doRecommendTask) {
  Write-Host "==> Recommend/apply best-loop execute task cadence" -ForegroundColor Cyan
  $taskArgs = @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $setBestLoopTask,
    "-WorkspaceRoot",
    $WorkspaceRoot,
    "-LoopMatrixPath",
    $LoopMatrixOut,
    "-TaskName",
    $BestLoopTaskName,
    "-SkipNoChangeAlertThreshold",
    "$BestLoopSkipNoChangeAlertThreshold",
    "-MinBestTestScore",
    "$BestLoopMinTestScore",
    "-MinBestStability",
    "$BestLoopMinStability"
  )
  if ($ApplyBestLoopTask) {
    $taskArgs += "-Apply"
  }
  if ($ApplyBestLoopTaskOnChangeOnly) {
    $taskArgs += "-ApplyOnChangeOnly"
  }
  powershell @taskArgs
  if ($LASTEXITCODE -ne 0) { throw "best-loop task cadence step failed: $LASTEXITCODE" }
}

$doPilot = $RunPilotSmoke -or (-not $SkipPilotSmoke)
if (-not $doPilot) {
  Write-Host "Chain complete (pilot smoke skipped)." -ForegroundColor Green
  exit 0
}

$pilotArgs = @(
  "-NoProfile",
  "-ExecutionPolicy",
  "Bypass",
  "-File",
  $pilot,
  "-RiskJson",
  $OutRiskJson
)
if ($EnableTacticalLong) {
  $pilotArgs += @(
    "-EnableTacticalLong",
    "-TacticalMaxQty", "$TacticalMaxQty",
    "-TacticalMinBreadthRatio", "$TacticalMinBreadthRatio",
    "-TacticalMinNetBuyKrwEok", "$TacticalMinNetBuyKrwEok",
    "-TacticalMinThemeScore", "$TacticalMinThemeScore"
  )
}

Write-Host "==> Run pilot smoke (dry by default)" -ForegroundColor Cyan
powershell @pilotArgs
if ($LASTEXITCODE -ne 0) { throw "pilot smoke failed: $LASTEXITCODE" }

Write-Host "Chain complete (including pilot smoke)." -ForegroundColor Green
exit 0

