#Requires -Version 5.1
<#
.SYNOPSIS
  Parallel B-track sweep: deadzone/HOLD, per-date combo, lens combo backtest, headline refresh.

.DESCRIPTION
  research_only / [HYPO]. Does not enable live trading or overwrite Track A active KPI without operator sign-off.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipMarketFetch,
    [switch]$SkipBacktest,
    [switch]$SkipHeadlineRefresh
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$py = Join-Path $env:WINDIR "py.exe"
if (-not (Test-Path -LiteralPath $py)) {
    $py = (Get-Command -Name "py" -ErrorAction Stop).Source
}

$scoreRec = Join-Path $WorkspaceRoot "reports\btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
$perDate180 = Join-Path $WorkspaceRoot "reports\btrack_ensemble_per_date_directions_180d_v1_latest.json"
$btc = Join-Path $WorkspaceRoot "research\market_data\btc_daily_external_yf.csv"
$kospi = Join-Path $WorkspaceRoot "research\market_data\kospi_daily_external_yf.csv"

$jobs = New-Object System.Collections.Generic.List[object]

if (-not $SkipMarketFetch) {
    $jobs.Add((Start-Job -ScriptBlock {
        param($Root, $Py)
        Set-Location $Root
        & $Py scripts/fetch_kospi_yfinance_csv.py 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { exit 1 }
        & $Py scripts/fetch_btc_yfinance_csv.py 2>&1 | Out-Null
        exit [int]$LASTEXITCODE
    } -ArgumentList $WorkspaceRoot, $py))
}

$jobs.Add((Start-Job -ScriptBlock {
    param($Root, $Py, $Score, $PerDate)
    Set-Location $Root
    & $Py scripts/sweep_prophecy_headline_deadzone_hold_v1.py `
        --score-json $Score `
        --per-date-json $PerDate `
        --min-coverage-active 0.55
    exit [int]$LASTEXITCODE
} -ArgumentList $WorkspaceRoot, $py, $scoreRec, $perDate180))

$jobs.Add((Start-Job -ScriptBlock {
    param($Root, $Py, $Score, $Kospi, $Btc)
    Set-Location $Root
    & $Py scripts/run_prophecy_per_date_lens_combo_sweep_v1.py `
        --score-json $Score `
        --kospi-csv $Kospi `
        --btc-csv $Btc `
        --deadzone-grid "0.0,0.001,0.003,0.005,0.01,0.02" `
        --top-k 12 `
        --output (Join-Path $Root "reports\prophecy_per_date_lens_combo_sweep_headline180_v1_latest.json")
    exit [int]$LASTEXITCODE
} -ArgumentList $WorkspaceRoot, $py, $scoreRec, $kospi, $btc))

if (-not $SkipBacktest) {
    $jobs.Add((Start-Job -ScriptBlock {
        param($Root, $Py)
        Set-Location $Root
        foreach ($dz in @("0.001", "0.003", "0.005", "0.01")) {
            $out = Join-Path $Root "reports\prophecy_lens_combo_backtest_deadzone_${dz}_v1_latest.json"
            & $Py scripts/run_prophecy_lens_combo_backtest_v1.py `
                --coordinator-deadzone $dz `
                --output $out 2>&1 | Out-Null
            if ($LASTEXITCODE -ne 0) { exit 1 }
        }
        exit 0
    } -ArgumentList $WorkspaceRoot, $py))
}

Write-Host "Parallel jobs started: $($jobs.Count)" -ForegroundColor Cyan
$null = $jobs | Wait-Job
foreach ($j in $jobs) {
    $out = Receive-Job -Job $j
    if ($out) { $out | ForEach-Object { Write-Host $_ } }
    if ($j.State -ne "Completed") {
        throw "Parallel job $($j.Id) ended state=$($j.State)"
    }
    Remove-Job -Job $j -Force
}

$sweepOut = Join-Path $WorkspaceRoot "reports\prophecy_headline_deadzone_hold_sweep_v1_latest.json"
if (-not (Test-Path -LiteralPath $sweepOut)) {
    Write-Host "WARN: deadzone hold sweep missing — re-running serial" -ForegroundColor Yellow
    & $py scripts/sweep_prophecy_headline_deadzone_hold_v1.py --score-json $scoreRec --per-date-json $perDate180
    if ($LASTEXITCODE -ne 0) { throw "deadzone hold sweep failed" }
}

$comboOut = Join-Path $WorkspaceRoot "reports\prophecy_per_date_lens_combo_sweep_headline180_v1_latest.json"
if (-not (Test-Path -LiteralPath $comboOut)) {
    Write-Host "WARN: per-date combo sweep missing — re-running serial" -ForegroundColor Yellow
    & $py scripts/run_prophecy_per_date_lens_combo_sweep_v1.py `
        --score-json $scoreRec --kospi-csv $kospi --btc-csv $btc `
        --deadzone-grid "0.0,0.001,0.003,0.005,0.01,0.02" `
        --output $comboOut
    if ($LASTEXITCODE -ne 0) { throw "per-date combo sweep failed" }
}

if (-not $SkipHeadlineRefresh) {
    Write-Host ""
    Write-Host "==> Headline parallel push (score+eval+observations)" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File `
        (Join-Path $WorkspaceRoot "scripts\Invoke-BtrackPerDateHeadlineParallelPush_v1.ps1") `
        -SkipMarketDataRefresh -SkipAmsaengBundle
    if ($LASTEXITCODE -ne 0) { throw "headline push failed exit=$LASTEXITCODE" }
}

Write-Host ""
Write-Host "[OK] Parallel deadzone/HOLD sweep complete" -ForegroundColor Green
Write-Host "  $sweepOut"
Write-Host "  $comboOut"
