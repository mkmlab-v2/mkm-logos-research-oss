#Requires -Version 5.1
<#
.SYNOPSIS
  Daily A-track KOSPI macro inputs refresh (07:50 task entrypoint).

.DESCRIPTION
  Wrapper for scripts/refresh_atrack_kospi_inputs_from_market_v1.py.
  Optionally refreshes KOSPI OHLCV CSV used by prophecy eval.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipKospiCsvFetch
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

if (-not $SkipKospiCsvFetch) {
    $kospiFetch = Join-Path $WorkspaceRoot "scripts\fetch_kospi_yfinance_csv.py"
    if (Test-Path -LiteralPath $kospiFetch) {
        Write-Host "==> fetch_kospi_yfinance_csv.py" -ForegroundColor Cyan
        & py $kospiFetch
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "fetch_kospi_yfinance_csv.py exit $LASTEXITCODE (continuing inputs refresh)"
        }
    }
}

$runner = Join-Path $WorkspaceRoot "scripts\refresh_atrack_kospi_inputs_from_market_v1.py"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing: $runner"
}

Write-Host "==> refresh_atrack_kospi_inputs_from_market_v1.py" -ForegroundColor Cyan
& py $runner
if ($LASTEXITCODE -ne 0) {
    throw "refresh_atrack_kospi_inputs_from_market_v1.py exit $LASTEXITCODE"
}

Write-Host "[OK] A-track KOSPI inputs refreshed." -ForegroundColor Green
