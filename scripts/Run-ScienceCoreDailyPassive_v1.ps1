<#
.SYNOPSIS
  Science Core daily passive accumulation — OHLCV refresh + per-date rebuild + governance [HYPO][research_only].

.DESCRIPTION
  Lighter than weekly MKM_ScienceCore_WeeklyGovernance (no long walk-forward / triple sweep / humanist AB).
  Intended for MKM-BTrack-DailyHypothesis-Chain -IncludeScienceCoreLane.
#>
[CmdletBinding()]
param(
    [string]$DateFrom = "2026-01-01",
    [string]$DateTo = "",
    [switch]$SkipOhlcvFetch
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $DateTo) {
    $DateTo = (Get-Date -Format "yyyy-MM-dd")
}

if (-not $SkipOhlcvFetch) {
    Write-Host "==> fetch_kospi_yfinance_csv.py (--merge --fill-recent-gaps)" -ForegroundColor Cyan
    py scripts/fetch_kospi_yfinance_csv.py --start 1990-01-01 --merge --fill-recent-gaps
    if ($LASTEXITCODE -ne 0) { throw "fetch kospi exit $LASTEXITCODE" }

    Write-Host "==> fetch_btc_yfinance_csv.py (--start 2010-01-01 --end $DateTo)" -ForegroundColor Cyan
    py scripts/fetch_btc_yfinance_csv.py --start 2010-01-01 --end $DateTo
    if ($LASTEXITCODE -ne 0) { throw "fetch btc exit $LASTEXITCODE" }
}

$bundleArgs = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
    (Join-Path $root "scripts\Run-ScienceCoreGovernanceBundle_v1.ps1"),
    "-DateFrom", $DateFrom,
    "-DateTo", $DateTo,
    "-UseFullHumanistPerDate",
    "-RebuildScience",
    "-RunPnlBootstrap"
)
Write-Host "==> Run-ScienceCoreGovernanceBundle_v1.ps1 (daily passive)" -ForegroundColor Cyan
& powershell @bundleArgs
if ($LASTEXITCODE -ne 0) { throw "science core daily passive governance exit $LASTEXITCODE" }

Write-Host "OK: science_core daily passive through $DateTo" -ForegroundColor Green
