# Binance USD-M pilot: Fact-Safe gate (--backend api) + one-shot executor.
# Default = dry only (no HTTP order). Testnet live vs mainnet small live are separate explicit paths.
#
# Dry (CI / no keys):
#   pwsh -NoProfile -File scripts/Run-BinanceUsdmPilotSmoke.ps1
#
# Testnet live (tiny qty; testnet API keys):
#   pwsh -NoProfile -File scripts/Run-BinanceUsdmPilotSmoke.ps1 -LiveTestnet -AcknowledgeLiveTestnet `
#     -RiskJson "projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json"
#
# Mainnet SMALL real (irreversible — run only on commander PC after manual review):
#   Use -Qty that satisfies exchange LOT_SIZE (BTCUSDT is typically 0.001 step, min 0.001 — not 0.0005).
#   Requires `reports/trading_human_execution_approval_latest.json` (trading_human_execution_approval_v1 GO) unless -SkipHumanApproval.
#   pwsh -NoProfile -File scripts/Run-BinanceUsdmPilotSmoke.ps1 -LiveMainnetSmall -AcknowledgeLiveMainnetSmall -AcknowledgeIrreversibleLoss `
#     -RiskJson "projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json" -Qty 0.001 -MaxMainnetQty 0.002
#
param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$RiskJson = "",
  [string]$Symbol = "BTCUSDT",
  [ValidateSet("BUY", "SELL")]
  [string]$Side = "BUY",
  [double]$Qty = 0.001,
  [double]$MaxMainnetQty = 0.002,
  [int]$Leverage = 2,
  [switch]$LiveTestnet,
  [switch]$AcknowledgeLiveTestnet,
  [switch]$LiveMainnetSmall,
  [switch]$AcknowledgeLiveMainnetSmall,
  [switch]$AcknowledgeIrreversibleLoss,
  [switch]$EnableTacticalLong,
  [double]$TacticalMaxQty = 0.002,
  [double]$TacticalMinBreadthRatio = 1.05,
  [double]$TacticalMinNetBuyKrwEok = 30000.0,
  [double]$TacticalMinThemeScore = 0.70,
  [switch]$SkipGateDryRun,
  [switch]$SkipExecutorDryRun,
  [string]$HumanApprovalJson = "",
  [switch]$SkipHumanApproval
)
$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

$fixtureRisk = (Resolve-Path -LiteralPath (Join-Path $WorkspaceRoot "tests\fixtures\risk_profile_fact_safe_gate_pass_minimal_v1.json")).Path

if ($LiveTestnet -and $LiveMainnetSmall) {
  throw "Use either -LiveTestnet or -LiveMainnetSmall, not both."
}

if ([string]::IsNullOrWhiteSpace($RiskJson)) {
  if ($LiveTestnet -or $LiveMainnetSmall) {
    throw "Live modes require explicit -RiskJson (Fact-Safe profile path). Test fixture is not allowed for live."
  }
  $RiskJson = $fixtureRisk
} elseif (-not [System.IO.Path]::IsPathRooted($RiskJson)) {
  $RiskJson = Join-Path $WorkspaceRoot $RiskJson
}
$RiskJson = (Resolve-Path -LiteralPath $RiskJson).Path

if (-not (Test-Path -LiteralPath $RiskJson)) {
  throw "Risk JSON not found: $RiskJson"
}

if ($LiveTestnet) {
  if (-not $AcknowledgeLiveTestnet) {
    throw "Live testnet requires -AcknowledgeLiveTestnet."
  }
}

if ($LiveMainnetSmall) {
  if (-not $AcknowledgeLiveMainnetSmall) {
    throw "Mainnet live requires -AcknowledgeLiveMainnetSmall."
  }
  if (-not $AcknowledgeIrreversibleLoss) {
    throw "Mainnet live requires -AcknowledgeIrreversibleLoss (real funds at risk)."
  }
  if ($RiskJson -ieq $fixtureRisk) {
    throw "Mainnet live cannot use the test fixture risk JSON; pass your real risk_profile path."
  }
  if ($Qty -le 0) {
    throw "-Qty must be positive."
  }
  $cap = $MaxMainnetQty
  if ($env:MKM_PILOT_MAINNET_MAX_QTY) {
    try {
      $envCap = [double]::Parse($env:MKM_PILOT_MAINNET_MAX_QTY, [System.Globalization.CultureInfo]::InvariantCulture)
      if ($envCap -gt 0) { $cap = [Math]::Min($cap, $envCap) }
    } catch { }
  }
  if ($Qty -gt $cap) {
    throw "Mainnet pilot: -Qty ($Qty) exceeds cap ($cap). Lower -Qty or raise -MaxMainnetQty only after policy review (env MKM_PILOT_MAINNET_MAX_QTY can lower ceiling)."
  }
}

$gate = "projects/bitcoin-trading/scripts/run_conditional_action_gate_v1.py"
$exec = "projects/bitcoin-trading/scripts/execute_binance_usdm_single_order_v1.py"
$tacticalGateArgs = @()
if ($EnableTacticalLong) {
  $tacticalGateArgs = @(
    "--enable-tactical-long",
    "--tactical-max-qty", "$TacticalMaxQty",
    "--tactical-min-breadth-ratio", "$TacticalMinBreadthRatio",
    "--tactical-min-net-buy-krw-eok", "$TacticalMinNetBuyKrwEok",
    "--tactical-min-theme-score", "$TacticalMinThemeScore"
  )
}

if (-not $SkipGateDryRun) {
  Write-Host "==> Gate dry-run (--backend api)" -ForegroundColor Cyan
  py $gate --backend api --dry-run --risk-json $RiskJson --symbol $Symbol --side $Side --qty $Qty --leverage $Leverage @tacticalGateArgs
  if ($LASTEXITCODE -ne 0) { throw "gate dry-run exit $LASTEXITCODE" }
}

if (-not $SkipExecutorDryRun) {
  Write-Host "==> Executor dry-run (no --live; writes intent summary)" -ForegroundColor Cyan
  $dryOut = "reports/binance_usdm_single_order/pilot_smoke_dry_run_latest.json"
  $dryExecArgs = @($exec, "--symbol", $Symbol, "--side", $Side, "--qty", "$Qty", "--leverage", "$Leverage", "--out", $dryOut)
  if ($LiveMainnetSmall) {
    $dryExecArgs += "--mainnet"
  }
  py @dryExecArgs
  if ($LASTEXITCODE -ne 0) { throw "executor dry-run exit $LASTEXITCODE" }
}

if (-not $LiveTestnet -and -not $LiveMainnetSmall) {
  Write-Host "Pilot smoke complete (dry only). Testnet: -LiveTestnet -AcknowledgeLiveTestnet -RiskJson <fact_safe>. Mainnet small: -LiveMainnetSmall -AcknowledgeLiveMainnetSmall -AcknowledgeIrreversibleLoss -RiskJson <fact_safe> -Qty ..." -ForegroundColor Green
  exit 0
}

if ($LiveTestnet) {
  if ($RiskJson -ieq $fixtureRisk) {
    Write-Host "WARN: Live testnet using repo TEST FIXTURE — prefer real -RiskJson for operational pilot." -ForegroundColor Yellow
  }
  Write-Host "==> Gate pass + LIVE testnet order" -ForegroundColor Yellow
  $out = "reports/binance_usdm_single_order/pilot_smoke_live_testnet_latest.json"
  py $gate --backend api --risk-json $RiskJson --symbol $Symbol --side $Side --qty $Qty --leverage $Leverage --pass-live @tacticalGateArgs --executor-out $out
  if ($LASTEXITCODE -ne 0) { throw "gate+live testnet exit $LASTEXITCODE" }
  Write-Host "Done. Summary: $out" -ForegroundColor Green
  exit 0
}

# LiveMainnetSmall
Write-Host "==> MAINNET small live (irreversible). Gate + executor --live --mainnet" -ForegroundColor Red
$hapArgs = @()
if (-not $SkipHumanApproval) {
  if ([string]::IsNullOrWhiteSpace($HumanApprovalJson)) {
    $hap = Join-Path $WorkspaceRoot "reports/trading_human_execution_approval_latest.json"
  } else {
    $hap = if ([System.IO.Path]::IsPathRooted($HumanApprovalJson)) { $HumanApprovalJson } else { (Join-Path $WorkspaceRoot $HumanApprovalJson) }
  }
  if (-not (Test-Path -LiteralPath $hap)) {
    throw "Mainnet small requires human approval JSON (default: reports/trading_human_execution_approval_latest.json). Create a GO receipt, or pass -HumanApprovalJson <path>, or -SkipHumanApproval (emergency only)."
  }
  $hapArgs = @("--human-approval-json", (Resolve-Path -LiteralPath $hap).Path)
}
$outM = "reports/binance_usdm_single_order/pilot_smoke_live_mainnet_small_latest.json"
py $gate --backend api --risk-json $RiskJson --symbol $Symbol --side $Side --qty $Qty --leverage $Leverage --pass-live --mainnet @tacticalGateArgs @hapArgs --executor-out $outM
if ($LASTEXITCODE -ne 0) { throw "gate+live mainnet exit $LASTEXITCODE" }
Write-Host "Done. Summary: $outM" -ForegroundColor Green
