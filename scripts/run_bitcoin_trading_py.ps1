<#
.SYNOPSIS
  Run py with PYTHONPATH scoped to projects/bitcoin-trading (not workspace root).

.DESCRIPTION
  Narrows import resolution to the trading project tree so diag_pid_tracker and
  process lists show clearer separation from MCP/tools. Changes directory to
  that project before invoking py.

.EXAMPLE
  & c:\workspace\scripts\run_bitcoin_trading_py.ps1 -m pytest tests/test_dual_regime_api_smoke.py -q
.EXAMPLE
  & c:\workspace\scripts\run_bitcoin_trading_py.ps1 scripts\run_forced_watch_alert_test.py
#>
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PyArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$WorkspaceRoot = Split-Path -Parent $PSScriptRoot
$Proj = Join-Path $WorkspaceRoot "projects\bitcoin-trading"

if (-not (Test-Path -LiteralPath $Proj)) {
    throw "bitcoin-trading project not found: $Proj"
}

$env:PYTHONPATH = $Proj
Push-Location -LiteralPath $Proj
try {
    if (-not $PyArgs -or $PyArgs.Count -eq 0) {
        Write-Host "Usage: pass py arguments after the script name, e.g. -m pytest ..." -ForegroundColor Yellow
        exit 1
    }
    & py @PyArgs
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
