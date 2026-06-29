<#
.SYNOPSIS
  Science Core KOSPI Mode B — shock/calm attach + news/macro ablation [HYPO][research_only].

.NOTES
  Does not enable Track A or live trading. BTC arms skipped in interpretation.
#>
[CmdletBinding()]
param(
    [string]$DateFrom = "2026-01-01",
    [string]$DateTo = "",
    [string]$HoldoutFrom = "2026-05-01",
    [string]$HoldoutTo = "",
    [switch]$SkipDailyPassive
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $DateTo) { $DateTo = (Get-Date -Format "yyyy-MM-dd") }
if (-not $HoldoutTo) { $HoldoutTo = $DateTo }

if (-not $SkipDailyPassive) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Run-ScienceCoreDailyPassive_v1.ps1") `
        -DateFrom $DateFrom -DateTo $DateTo
    if ($LASTEXITCODE -ne 0) { throw "daily passive exit $LASTEXITCODE" }
}

Write-Host "==> build_science_core_shock_discordant_day_report_v1.py" -ForegroundColor Cyan
py scripts/build_science_core_shock_discordant_day_report_v1.py --date-from $HoldoutFrom --date-to $HoldoutTo
if ($LASTEXITCODE -ne 0) { throw "shock discordant report exit $LASTEXITCODE" }

Write-Host "==> run_science_core_news_weight_ablation_v1.py" -ForegroundColor Cyan
py scripts/run_science_core_news_weight_ablation_v1.py `
    --date-from $DateFrom --date-to $DateTo `
    --holdout-from $HoldoutFrom --holdout-to $HoldoutTo
if ($LASTEXITCODE -ne 0) { throw "news weight ablation exit $LASTEXITCODE" }

Write-Host "==> run_science_core_conditional_attach_research_v1.py" -ForegroundColor Cyan
py scripts/run_science_core_conditional_attach_research_v1.py
if ($LASTEXITCODE -ne 0) { throw "conditional attach research exit $LASTEXITCODE" }

Write-Host "==> run_science_core_kospi_shock_only_attach_backtest_v1.py" -ForegroundColor Cyan
py scripts/run_science_core_kospi_shock_only_attach_backtest_v1.py --date-from $HoldoutFrom --date-to $HoldoutTo
if ($LASTEXITCODE -ne 0) { throw "shock-only attach backtest exit $LASTEXITCODE" }

Write-Host "==> run_science_core_governance_bundle_v1.py (embed ablation)" -ForegroundColor Cyan
py scripts/run_science_core_governance_bundle_v1.py --date-from $DateFrom --date-to $DateTo --run-news-weight-ablation --run-pnl-bootstrap
if ($LASTEXITCODE -ne 0) { throw "governance embed ablation exit $LASTEXITCODE" }

Write-Host "==> build_science_core_instrument_matrix_v1.py" -ForegroundColor Cyan
py scripts/build_science_core_instrument_matrix_v1.py
if ($LASTEXITCODE -ne 0) { throw "instrument matrix exit $LASTEXITCODE" }

Write-Host "OK: Science Core KOSPI Mode B through $DateTo" -ForegroundColor Green
