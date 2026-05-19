#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot KPI-B operational headline refresh (market CSV + per-date WF + promote).

.DESCRIPTION
  Requires commander approval file btrack_dual_kpi_headline_human_approval_v1_latest.json.
  Does not enable live trading. Refreshes WF + promotion gates + runtime health + panel snapshot.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmBtrackKpiBOperationalRefresh_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipMarketFetch,
    [switch]$SkipPanel,
    [switch]$SkipWebhook
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$approval = Join-Path $WorkspaceRoot "docs\final\artifacts\btrack_dual_kpi_headline_human_approval_v1_latest.json"
if (-not (Test-Path -LiteralPath $approval)) {
    throw "Missing KPI-B approval: $approval (run apply_btrack_dual_kpi_headline_human_approval_v1.py first)"
}

if (-not $SkipMarketFetch) {
    Write-Host "==> fetch BTC/KOSPI CSV" -ForegroundColor Cyan
    py scripts/fetch_btc_yfinance_csv.py
    if ($LASTEXITCODE -ne 0) { throw "fetch_btc exit $LASTEXITCODE" }
    py scripts/fetch_kospi_yfinance_csv.py
    if ($LASTEXITCODE -ne 0) { throw "fetch_kospi exit $LASTEXITCODE" }
}

$btc = Join-Path $WorkspaceRoot "research\market_data\btc_daily_external_yf.csv"
$archive = "docs\final\artifacts\prophecy_hit_rate_eval_kpi_a_frozen_archive_v1_latest.json"
Write-Host "==> run_btrack_kpi_b_shadow_eval_v1.py --promote-to-operational-headline" -ForegroundColor Cyan
py scripts/run_btrack_kpi_b_shadow_eval_v1.py --btc-csv $btc --promote-to-operational-headline --kpi-a-eval-json $archive
if ($LASTEXITCODE -ne 0) { throw "kpi_b promote exit $LASTEXITCODE" }

Write-Host "==> walkforward + gates + runtime health" -ForegroundColor Cyan
py scripts/run_prophecy_per_date_combo_walkforward_v1.py --score-json docs/final/artifacts/btrack_prophecy_score_latest.json
if ($LASTEXITCODE -ne 0) { throw "walkforward exit $LASTEXITCODE" }
py scripts/eval_prophecy_promotion_gates_v1.py --promotion-track-mode btc_only_crossassist
if ($LASTEXITCODE -ne 0) { throw "gates exit $LASTEXITCODE" }
py scripts/evaluate_prophecy_runtime_health_v1.py --operation-mode-b-shadow
if ($LASTEXITCODE -ne 0) { Write-Host "WARN: runtime health exit $LASTEXITCODE" -ForegroundColor Yellow }
py scripts/build_prophecy_health_status_v1.py
if ($LASTEXITCODE -ne 0) { Write-Host "WARN: health status exit $LASTEXITCODE" -ForegroundColor Yellow }

if (-not $SkipPanel) {
    $panelArgs = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", (Join-Path $WorkspaceRoot "scripts\Check-ProphecyPanel24hAlerts.ps1"),
        "-WorkspaceRoot", $WorkspaceRoot,
        "-OutJson", (Join-Path $WorkspaceRoot "reports\prophecy_panel_24h_alerts_latest.json"),
        "-AppendLog"
    )
    if ($SkipWebhook) { $panelArgs += "-SkipWebhook" }
    Write-Host "==> Check-ProphecyPanel24hAlerts.ps1" -ForegroundColor Cyan
    & powershell @panelArgs
    $panelRc = $LASTEXITCODE
    Write-Host "Panel exit: $panelRc" -ForegroundColor $(if ($panelRc -eq 0) { "Green" } else { "Yellow" })
}

Write-Host "[DONE] Invoke-MkmBtrackKpiBOperationalRefresh_v1.ps1" -ForegroundColor Green
