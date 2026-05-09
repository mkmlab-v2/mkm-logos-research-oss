[CmdletBinding()]
param(
  [string]$WorkspaceRoot = "",
  [string]$RiskJson = "projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json",
  [string]$Symbol = "BTCUSDT",
  [ValidateSet("AUTO", "BUY", "SELL")]
  [string]$ForceSide = "AUTO",
  [double]$Qty = 0.001,
  [double]$MaxMainnetQty = 0.002,
  [int]$Leverage = 1,
  [switch]$EnableTacticalLong,
  [switch]$ExecuteLiveMainnetSmall,
  [switch]$AcknowledgeLiveMainnetSmall,
  [switch]$AcknowledgeIrreversibleLoss,
  [switch]$AcknowledgeStoplinePolicyV1
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
  if (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
  } else {
    $WorkspaceRoot = (Get-Location).Path
  }
}

Set-Location -LiteralPath $WorkspaceRoot

$pilot = Join-Path $WorkspaceRoot "scripts\Run-BinanceUsdmPilotSmoke.ps1"
if (-not (Test-Path -LiteralPath $pilot)) {
  throw "Missing script: $pilot"
}

if (-not [System.IO.Path]::IsPathRooted($RiskJson)) {
  $RiskJson = Join-Path $WorkspaceRoot $RiskJson
}
$RiskJson = (Resolve-Path -LiteralPath $RiskJson).Path

$risk = Get-Content -LiteralPath $RiskJson -Raw | ConvertFrom-Json
$bridge = $risk.governance_bridge
$tri = $risk.trinity_governor

if (-not $bridge -or $bridge.final_action_allowed -ne $true) {
  throw "Risk governance bridge denies final action. Stop."
}

$riskLeverageCap = 1.0
if ($risk.leverage_multiplier_cap) {
  $riskLeverageCap = [double]$risk.leverage_multiplier_cap
}
$effectiveLeverage = [Math]::Min($Leverage, [int][Math]::Floor($riskLeverageCap))
if ($effectiveLeverage -lt 1) { $effectiveLeverage = 1 }

$riskQtyCap = $MaxMainnetQty
if ($risk.max_position_size) {
  $riskQtyCap = [Math]::Min($riskQtyCap, [double]$risk.max_position_size)
}
if ($Qty -gt $riskQtyCap) {
  throw "Qty ($Qty) exceeds risk cap ($riskQtyCap)."
}

$side = "BUY"
if ($ForceSide -eq "BUY" -or $ForceSide -eq "SELL") {
  $side = $ForceSide
} elseif ($tri -and $tri.core_decision -and "$($tri.core_decision)".ToUpperInvariant().Contains("SHORT")) {
  $side = "SELL"
}

Write-Host "Preset profile:"
Write-Host "  symbol=$Symbol side=$side qty=$Qty leverage=$effectiveLeverage"
Write-Host "  risk_mode=$($risk.mode) final_action_allowed=$($bridge.final_action_allowed)"
Write-Host "  caps qty<=$riskQtyCap leverage<=$riskLeverageCap"

$baseArgs = @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-File", $pilot,
  "-RiskJson", $RiskJson,
  "-Symbol", $Symbol,
  "-Side", $side,
  "-Qty", "$Qty",
  "-MaxMainnetQty", "$riskQtyCap",
  "-Leverage", "$effectiveLeverage"
)
if ($EnableTacticalLong -and $side -eq "BUY") {
  $baseArgs += "-EnableTacticalLong"
}

if (-not $ExecuteLiveMainnetSmall) {
  Write-Host "==> Dry validation only (gate/executor dry-run)" -ForegroundColor Cyan
  & powershell @baseArgs
  if ($LASTEXITCODE -ne 0) {
    throw "Dry validation failed (exit=$LASTEXITCODE)."
  }
  Write-Host "[ok] Dry validation complete. Use -ExecuteLiveMainnetSmall to place small live order." -ForegroundColor Green
  exit 0
}

if (-not ($AcknowledgeLiveMainnetSmall -and $AcknowledgeIrreversibleLoss -and $AcknowledgeStoplinePolicyV1)) {
  throw "Live mode requires -AcknowledgeLiveMainnetSmall -AcknowledgeIrreversibleLoss -AcknowledgeStoplinePolicyV1."
}

Write-Host "==> LIVE mainnet small validation" -ForegroundColor Yellow
$liveArgs = $baseArgs + @(
  "-LiveMainnetSmall",
  "-AcknowledgeLiveMainnetSmall",
  "-AcknowledgeIrreversibleLoss",
  "-AcknowledgeStoplinePolicyV1"
)
& powershell @liveArgs
if ($LASTEXITCODE -ne 0) {
  throw "Live validation failed (exit=$LASTEXITCODE)."
}
Write-Host "[ok] Live mainnet small validation complete." -ForegroundColor Green
