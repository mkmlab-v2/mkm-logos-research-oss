#Requires -Version 5.1
<#
.SYNOPSIS
  Parallel push: per-date directions (180d) -> recommended score -> hit-rate eval -> observation panels.

.DESCRIPTION
  B-track / research_only. Does not enable live trading or mutate Track A artifacts under docs/final/artifacts
  except prophecy_hit_rate_eval_latest.json (operator headline KPI).

  Phase A (parallel jobs): per-date 180d build, fusion stub refresh, optional amsaeng bundle.
  Phase B (serial): recommended eval chain with --per-date-direction-json, hit-rate eval, integrity gates, Track C dashboard.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$RecentTradingDays = 180,
    [string]$PerDateOutRel = "reports/btrack_ensemble_per_date_directions_180d_v1_latest.json",
    [switch]$SkipMarketDataRefresh,
    [switch]$SkipAmsaengBundle,
    [switch]$SkipFusionStub,
    [switch]$SkipRecommendedChain,
    [switch]$SkipDashboard,
    [double]$NeutralBps = 4.0
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$py = Join-Path $env:WINDIR "py.exe"
if (-not (Test-Path -LiteralPath $py)) {
    $py = (Get-Command -Name "py" -ErrorAction Stop).Source
}

$btcDefault = Join-Path $WorkspaceRoot "research\market_data\btc_daily_external_yf.csv"
$kospiDefault = Join-Path $WorkspaceRoot "research\market_data\kospi_daily_external_yf.csv"
$perDatePath = Join-Path $WorkspaceRoot ($PerDateOutRel -replace "/", "\")
$scoreRecommended = Join-Path $WorkspaceRoot "reports\btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
$hitEvalLatest = Join-Path $WorkspaceRoot "docs\final\artifacts\prophecy_hit_rate_eval_latest.json"

function Invoke-StepPy {
    param([string]$Label, [string[]]$Args, [switch]$AllowNonZero)
    Write-Host ""
    Write-Host "==> $Label" -ForegroundColor Cyan
    & $py @Args
    $code = [int]$LASTEXITCODE
    if ($code -ne 0 -and -not $AllowNonZero) {
        throw "$Label failed exit=$code"
    }
    return $code
}

# --- Phase A: parallel ---
$jobs = New-Object System.Collections.Generic.List[object]

if (-not $SkipMarketDataRefresh) {
    $jobs.Add((Start-Job -ScriptBlock {
        param($Root, $Py, $Kospi, $Btc)
        Set-Location $Root
        & $Py scripts/fetch_kospi_yfinance_csv.py 2>&1 | Out-Null
        $a = $LASTEXITCODE
        & $Py scripts/fetch_btc_yfinance_csv.py 2>&1 | Out-Null
        $b = $LASTEXITCODE
        if ($a -ne 0 -or $b -ne 0) { exit 1 }
        exit 0
    } -ArgumentList $WorkspaceRoot, $py, $kospiDefault, $btcDefault))
}

$jobs.Add((Start-Job -ScriptBlock {
    param($Root, $Py, $Days, $OutRel, $Btc, $Kospi)
    Set-Location $Root
    $out = Join-Path $Root ($OutRel -replace "/", "\")
    & $Py scripts/build_btrack_ensemble_per_date_directions_v1.py `
        --recent-trading-days $Days `
        --target-instrument btc `
        --btc-csv $Btc `
        --kospi-csv $Kospi `
        --output $out
    exit [int]$LASTEXITCODE
} -ArgumentList $WorkspaceRoot, $py, $RecentTradingDays, $PerDateOutRel, $btcDefault, $kospiDefault))

if (-not $SkipFusionStub) {
    $jobs.Add((Start-Job -ScriptBlock {
        param($Root, $Py)
        Set-Location $Root
        & $Py scripts/report_independent_lens_fusion_stub_v0.py
        exit [int]$LASTEXITCODE
    } -ArgumentList $WorkspaceRoot, $py))
}

if (-not $SkipAmsaengBundle) {
    $bundlePs1 = Join-Path $WorkspaceRoot "scripts\Run-AmsaengEosaMonitoringBundleTask.ps1"
    if (Test-Path -LiteralPath $bundlePs1) {
        $jobs.Add((Start-Job -ScriptBlock {
            param($Bundle)
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Bundle
            exit [int]$LASTEXITCODE
        } -ArgumentList $bundlePs1))
    }
}

Write-Host "Phase A: waiting on $($jobs.Count) parallel job(s)..." -ForegroundColor Yellow
$jobResults = $jobs | Wait-Job
foreach ($j in $jobResults) {
    $name = $j.Name
    if ($j.State -eq "Failed" -or $j.ChildJobs[0].JobStateInfo.State -eq "Failed") {
        Receive-Job $j -ErrorAction SilentlyContinue | Out-Host
        Write-Host "WARN: job $name failed (non-fatal for Phase B if per-date built)" -ForegroundColor Yellow
    } else {
        $code = (Receive-Job $j)
        Write-Host "job $name exit=$code" -ForegroundColor DarkGray
    }
    Remove-Job $j -Force -ErrorAction SilentlyContinue
}

if (-not (Test-Path -LiteralPath $perDatePath)) {
    throw "Per-date directions missing after Phase A: $perDatePath"
}
Write-Host "Per-date OK: $perDatePath" -ForegroundColor Green

# Mirror to v1_latest for daily chain / advisory consumers
$v1Latest = Join-Path $WorkspaceRoot "reports\btrack_ensemble_per_date_directions_v1_latest.json"
Copy-Item -LiteralPath $perDatePath -Destination $v1Latest -Force

# Phase B: score + eval (always; faster than full WF chain)
if (-not (Test-Path -LiteralPath $btcDefault)) {
    throw "BTC CSV required after market refresh: $btcDefault"
}
$buildArgs = @(
    "scripts/build_btrack_prophecy_score_from_ohlcv.py",
    "--recent-trading-days", "$RecentTradingDays",
    "--force-dual-leg-panel",
    "--neutral-bps", "$NeutralBps",
    "--btc-csv", "research/market_data/btc_daily_external_yf.csv",
    "--per-date-direction-json", $PerDateOutRel,
    "--output", "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
)
Invoke-StepPy -Label "build score (per-date + dual-leg)" -Args $buildArgs | Out-Null

Invoke-StepPy -Label "eval_prophecy_hit_rate -> latest" -Args @(
    "scripts/eval_prophecy_hit_rate_v1.py",
    "--run-mode", "price",
    "--score-json", "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json",
    "--output", "docs/final/artifacts/prophecy_hit_rate_eval_latest.json",
    "--allow-headline-write"
) | Out-Null

if (-not $SkipRecommendedChain) {
    $recArgs = @(
        "scripts/run_prophecy_btrack_recommended_eval_chain_v1.py",
        "--recent-trading-days", "$RecentTradingDays",
        "--neutral-bps", "$NeutralBps",
        "--per-date-direction-json", $PerDateOutRel
    )
    Invoke-StepPy -Label "recommended eval chain WF + gates (optional slow)" -Args $recArgs -AllowNonZero | Out-Null
}

Invoke-StepPy -Label "coordinator lens conflict observation" -Args @(
    "scripts/check_coordinator_lens_conflict_observation_v1.py"
) -AllowNonZero | Out-Null

Invoke-StepPy -Label "prophecy headline integrity observation" -Args @(
    "scripts/check_prophecy_headline_integrity_v1.py"
) -AllowNonZero | Out-Null

if (-not $SkipDashboard) {
    Invoke-StepPy -Label "build_mkm_trackc_ops_dashboard" -Args @(
        "scripts/build_mkm_trackc_ops_dashboard_v1.py"
    ) -AllowNonZero | Out-Null
}

Write-Host ""
Write-Host "[OK] B-track per-date headline parallel push complete" -ForegroundColor Green
Write-Host "  per-date: $PerDateOutRel" -ForegroundColor DarkGray
Write-Host "  score:    reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json" -ForegroundColor DarkGray
Write-Host "  hit-rate: docs/final/artifacts/prophecy_hit_rate_eval_latest.json" -ForegroundColor DarkGray
Write-Host "  observe:  reports/coordinator_lens_conflict_observation_latest.json" -ForegroundColor DarkGray
Write-Host "          reports/prophecy_headline_integrity_observation_latest.json" -ForegroundColor DarkGray
