param(
  [string]$TaskName = "\MKM-Trading-Execution-Chain-Once",
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [int]$WaitSeconds = 20,
  [switch]$OfferMainnetPilot,
  [switch]$RunMainnetPilotNow,
  [switch]$AcknowledgeIrreversibleLoss
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-JsonSafe([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) { return $null }
  try {
    return Get-Content -LiteralPath $Path -Encoding UTF8 -Raw | ConvertFrom-Json -Depth 20
  } catch {
    return $null
  }
}

Write-Host "==> Run task: $TaskName" -ForegroundColor Cyan
schtasks /Run /TN $TaskName | Out-Null

if ($WaitSeconds -gt 0) {
  Write-Host "==> Waiting ${WaitSeconds}s for artifacts..." -ForegroundColor Cyan
  Start-Sleep -Seconds $WaitSeconds
}

$proposalPath = Join-Path $WorkspaceRoot "reports\trading_execution_proposal_latest.json"
$approvalPath = Join-Path $WorkspaceRoot "reports\trading_human_execution_approval_latest.json"
$statusPath = Join-Path $WorkspaceRoot "docs\final\artifacts\trading_go_no_go_latest.json"

$proposal = Get-JsonSafe $proposalPath
$approval = Get-JsonSafe $approvalPath
$status = Get-JsonSafe $statusPath

Write-Host ""
Write-Host "=== Trading Execution Chain Snapshot ===" -ForegroundColor Green
Write-Host ("proposal: {0}" -f $(if ($proposal) { "ok" } else { "missing/invalid" }))
if ($proposal) {
  Write-Host ("  proposal_id: {0}" -f $proposal.proposal_id)
  Write-Host ("  intent: {0}" -f $proposal.intent_summary)
}
Write-Host ("approval: {0}" -f $(if ($approval) { "ok" } else { "missing/invalid" }))
if ($approval) {
  Write-Host ("  decision: {0}" -f $approval.decision)
  Write-Host ("  valid_until_utc: {0}" -f $approval.valid_until_utc)
  Write-Host ("  proposal_id: {0}" -f $approval.proposal_id)
}
Write-Host ("go_no_go: {0}" -f $(if ($status) { "ok" } else { "missing/invalid" }))
if ($status) {
  Write-Host ("  go_no_go: {0}" -f $status.go_no_go)
  Write-Host ("  reasons: {0}" -f $(([string[]]$status.reasons) -join ", "))
  Write-Host ("  gate_reason: {0}" -f $status.gate_reason)
}

Write-Host ""
Write-Host "FILES:"
Write-Host "  $proposalPath"
Write-Host "  $approvalPath"
Write-Host "  $statusPath"

if ($OfferMainnetPilot -or $RunMainnetPilotNow) {
  Write-Host ""
  Write-Host "=== Mainnet Small Pilot Safety Prompt ===" -ForegroundColor Yellow
  if (-not $status -or $status.go_no_go -ne "GO") {
    Write-Host "[block] go_no_go is not GO. Do not run mainnet pilot." -ForegroundColor Red
    exit 1
  }
  $cmd = @(
    "pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/Run-BinanceUsdmPilotSmoke.ps1",
    "-LiveMainnetSmall -AcknowledgeLiveMainnetSmall -AcknowledgeIrreversibleLoss -AcknowledgeStoplinePolicyV1",
    "-RiskJson `"projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json`" -Qty 0.001 -MaxMainnetQty 0.002"
  ) -join " "
  Write-Host "[cmd] $cmd"
  if ($RunMainnetPilotNow) {
    if (-not $AcknowledgeIrreversibleLoss) {
      throw "RunMainnetPilotNow requires -AcknowledgeIrreversibleLoss."
    }
    Write-Host "==> Executing mainnet small pilot now..." -ForegroundColor Red
    pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts/Run-BinanceUsdmPilotSmoke.ps1") `
      -LiveMainnetSmall -AcknowledgeLiveMainnetSmall -AcknowledgeIrreversibleLoss -AcknowledgeStoplinePolicyV1 `
      -RiskJson (Join-Path $WorkspaceRoot "projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json") `
      -Qty 0.001 -MaxMainnetQty 0.002
  } else {
    Write-Host "[info] Preview only. Add -RunMainnetPilotNow -AcknowledgeIrreversibleLoss to execute." -ForegroundColor Yellow
  }
}

