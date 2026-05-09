[CmdletBinding()]
param(
  [string]$WorkspaceRoot = "",
  [string]$RiskJson = "projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json",
  [string]$Symbol = "BTCUSDT",
  [double]$Qty = 0.001,
  [double]$MaxMainnetQty = 0.002,
  [int]$Leverage = 1
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

$preset = Join-Path $WorkspaceRoot "scripts\Run-BinanceUsdmSmallValidationBestPreset.ps1"
if (-not (Test-Path -LiteralPath $preset)) {
  throw "Missing script: $preset"
}

Write-Host "==> Bi-directional dry validation: BUY" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File $preset `
  -WorkspaceRoot $WorkspaceRoot `
  -RiskJson $RiskJson `
  -Symbol $Symbol `
  -Qty $Qty `
  -MaxMainnetQty $MaxMainnetQty `
  -Leverage $Leverage `
  -ForceSide BUY
if ($LASTEXITCODE -ne 0) {
  throw "BUY dry validation failed (exit=$LASTEXITCODE)"
}

Write-Host "==> Bi-directional dry validation: SELL" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File $preset `
  -WorkspaceRoot $WorkspaceRoot `
  -RiskJson $RiskJson `
  -Symbol $Symbol `
  -Qty $Qty `
  -MaxMainnetQty $MaxMainnetQty `
  -Leverage $Leverage `
  -ForceSide SELL
if ($LASTEXITCODE -ne 0) {
  throw "SELL dry validation failed (exit=$LASTEXITCODE)"
}

Write-Host "[ok] Bi-directional dry validation complete (BUY/SELL)." -ForegroundColor Green
