param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$Symbol = "BTCUSDT",
  [ValidateSet("BUY", "SELL")]
  [string]$Side = "BUY",
  [double]$Qty = 0.001,
  [int]$Leverage = 2,
  [ValidateSet("mainnet_small", "testnet_live")]
  [string]$Target = "mainnet_small",
  [ValidateSet("GO", "NO_GO")]
  [string]$Decision = "GO",
  [string]$Approver = "commander",
  [int]$ValidHours = 24,
  [string]$Note = "Operator-reviewed execution proposal."
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location $WorkspaceRoot

$buildProposal = Join-Path $WorkspaceRoot "scripts\build_trading_execution_proposal_v1.py"
$applyVeto = Join-Path $WorkspaceRoot "scripts\apply_sasang_veto_to_trading_proposal_v1.py"
$approve = Join-Path $WorkspaceRoot "scripts\approve_trading_execution_v1.ps1"
$validate = Join-Path $WorkspaceRoot "scripts\validate_trading_human_execution_approval_v1.py"
$buildStatus = Join-Path $WorkspaceRoot "scripts\build_trading_go_nogo_status_v1.py"
$approvalPath = Join-Path $WorkspaceRoot "reports\trading_human_execution_approval_latest.json"
$vetoAdjustedPath = Join-Path $WorkspaceRoot "reports\trading_execution_proposal_veto_adjusted_latest.json"
$statusPath = Join-Path $WorkspaceRoot "docs\final\artifacts\trading_go_no_go_latest.json"

Write-Host "==> 1/5 Build trading execution proposal" -ForegroundColor Cyan
py $buildProposal --target $Target --symbol $Symbol --side $Side --qty $Qty --leverage $Leverage --note $Note
if ($LASTEXITCODE -ne 0) { throw "build_trading_execution_proposal_v1.py exit $LASTEXITCODE" }

Write-Host "==> 2/5 Apply sasang veto-only adjustment (if active)" -ForegroundColor Cyan
py $applyVeto
if ($LASTEXITCODE -ne 0) { throw "apply_sasang_veto_to_trading_proposal_v1.py exit $LASTEXITCODE" }

Write-Host "==> 3/5 Approve trading execution receipt" -ForegroundColor Cyan
pwsh -NoProfile -ExecutionPolicy Bypass -File $approve -Decision $Decision -Approver $Approver -ValidHours $ValidHours
if ($LASTEXITCODE -ne 0) { throw "approve_trading_execution_v1.ps1 exit $LASTEXITCODE" }

Write-Host "==> 4/5 Validate receipt hash/schema/expiry" -ForegroundColor Cyan
py $validate --approval $approvalPath
if ($LASTEXITCODE -ne 0) { throw "validate_trading_human_execution_approval_v1.py exit $LASTEXITCODE" }

Write-Host "==> 5/5 Build single GO/NO_GO status" -ForegroundColor Cyan
py $buildStatus
if ($LASTEXITCODE -eq 0) {
  Write-Host "[ok] Trading chain finished => GO" -ForegroundColor Green
} elseif ($LASTEXITCODE -eq 1) {
  Write-Host "[warn] Trading chain finished => NO_GO (see reasons)." -ForegroundColor Yellow
} else {
  throw "build_trading_go_nogo_status_v1.py exit $LASTEXITCODE"
}

if (Test-Path -LiteralPath $statusPath) {
  Write-Host "STATUS_FILE: $statusPath"
}
if (Test-Path -LiteralPath $vetoAdjustedPath) {
  Write-Host "VETO_ADJUSTED_FILE: $vetoAdjustedPath"
}

