<#
.SYNOPSIS
  Run BTC live-upgrade verification report immediately.
#>
param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

& py (Join-Path $WorkspaceRoot "scripts/build_btc_live_upgrade_verification_report.py")
if ($LASTEXITCODE -ne 0) { throw "build_btc_live_upgrade_verification_report.py failed: $LASTEXITCODE" }

Write-Host "OK: BTC live-upgrade verification generated." -ForegroundColor Green

