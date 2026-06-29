#Requires -Version 5.1
<#
.SYNOPSIS
  Parallel advance: B-track 10lane · KOSPI 30d · Logos OOS (optional) · lens hardening · Telegram.

.DESCRIPTION
  B-track / research_only. Start-Job lanes in parallel; OOS 120d restore if logos run clobbered gate.
  -IncludeBtrack10Lane includes KOSPI+BTC 30d inside 10lane — use -SkipKospiRebuild -SkipLogosRevalidation with it.
  -IncludeKospiParallel runs KOSPI 30d rebuild job alongside 10lane (overrides default skip when 10lane is on).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$IncludeBtrack10Lane,
    [switch]$IncludeKospiParallel,
    [switch]$SkipKospiRebuild,
    [switch]$SkipLogosRevalidation,
    [int]$Btrack10MaxWorkers = 6,
    [switch]$SendTelegram,
    [switch]$WhatIf
)

if ($IncludeKospiParallel) {
    $SkipKospiRebuild = $false
}
elseif ($IncludeBtrack10Lane -and -not $PSBoundParameters.ContainsKey('SkipKospiRebuild')) {
    $SkipKospiRebuild = $true
}
if ($IncludeBtrack10Lane -and -not $PSBoundParameters.ContainsKey('SkipLogosRevalidation')) {
    $SkipLogosRevalidation = $true
}

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

$kospiDualV2 = Join-Path $WorkspaceRoot "docs\final\artifacts\btrack_prophecy_score_kospi_dual_v2_per_date_latest.json"
$kospiParallel = Join-Path $WorkspaceRoot "docs\final\artifacts\btrack_prophecy_score_kospi_30d_dual_parallel_v1.json"
$sidecar = Join-Path $WorkspaceRoot "docs\final\artifacts\btrack_prophecy_score_insight_sidecar_v1_latest.json"
$btcCsv = Join-Path $WorkspaceRoot "research\market_data\btc_daily_external_yf.csv"
$kospiCsv = Join-Path $WorkspaceRoot "research\market_data\kospi_daily_external_yf.csv"
$hyp = Join-Path $WorkspaceRoot "docs\final\artifacts\btrack_hypothesis_prophecy_latest.json"

$lanes = @()

if (-not $SkipKospiRebuild) {
    $lanes += @{
        Name = "kospi_30d"
        Script = @"
Set-Location -LiteralPath '$WorkspaceRoot'
& '$py' scripts/fetch_kospi_yfinance_csv.py
if (`$LASTEXITCODE -ne 0) { throw 'fetch_kospi' }
& '$py' scripts/fetch_btc_yfinance_csv.py
if (`$LASTEXITCODE -ne 0) { throw 'fetch_btc' }
& '$py' scripts/generate_btrack_hypothesis_prophecy_v1.py --research-evaluation-instrument kospi
if (`$LASTEXITCODE -ne 0) { throw 'hypothesis_kospi' }
& '$py' scripts/build_btrack_prophecy_score_from_ohlcv.py --recent-trading-days 30 --force-dual-leg-panel --kospi-csv research/market_data/kospi_daily_external_yf.csv --btc-csv research/market_data/btc_daily_external_yf.csv --hypothesis-json docs/final/artifacts/btrack_hypothesis_prophecy_latest.json --output docs/final/artifacts/btrack_prophecy_score_kospi_30d_dual_parallel_v1.json
if (`$LASTEXITCODE -ne 0) { throw 'build_kospi_score' }
& '$py' scripts/eval_prophecy_hit_rate_v1.py --run-mode price --score-json docs/final/artifacts/btrack_prophecy_score_kospi_30d_dual_parallel_v1.json --headline-instrument kospi --output reports/prophecy_hit_rate_eval_kospi_30d_dual_parallel_v1_latest.json
if (`$LASTEXITCODE -ne 0) { throw 'eval_kospi' }
Write-Host '[OK] kospi_30d lane'
"@
    }
}

if (-not $SkipLogosRevalidation) {
    $lanes += @{
        Name = "logos_revalidation"
        Script = @"
Set-Location -LiteralPath '$WorkspaceRoot'
`$score = 'docs/final/artifacts/btrack_prophecy_score_latest.json'
`$side = '$sidecar'
if (-not (Test-Path -LiteralPath `$side)) { `$side = 'docs/final/artifacts/btrack_prophecy_score_insight_sidecar_30y_latest.json' }
& '$py' scripts/run_prophecy_logos_revalidation_suite_v1.py --score-json `$score --sidecar-json `$side --target-instrument btc --no-strict-shadow-forward-mode
if (`$LASTEXITCODE -ne 0) { throw 'logos_revalidation exit ' + `$LASTEXITCODE }
Write-Host '[OK] logos_revalidation lane'
"@
    }
}

if ($IncludeBtrack10Lane) {
    $lanes += @{
        Name = "btrack_10lane"
        Script = @"
Set-Location -LiteralPath '$WorkspaceRoot'
& '$py' scripts/run_btrack_parallel_10lane_v1.py --max-workers $Btrack10MaxWorkers --skip-weekly
if (`$LASTEXITCODE -ne 0) { throw 'btrack_10lane exit ' + `$LASTEXITCODE }
Write-Host '[OK] btrack_10lane'
"@
    }
}

if ($WhatIf) {
    foreach ($l in $lanes) { Write-Host "[WhatIf] $($l.Name)" }
    exit 0
}

$jobs = @()
foreach ($l in $lanes) {
    Write-Host ">> start job $($l.Name)" -ForegroundColor Cyan
    $jobs += Start-Job -Name $l.Name -ScriptBlock {
        param($body)
        Invoke-Expression $body
    } -ArgumentList $l.Script
}

$softFail = @("logos_revalidation", "btrack_10lane")
$fail = @()
foreach ($j in $jobs) {
    $null = Wait-Job -Job $j
    $out = Receive-Job -Job $j -ErrorAction SilentlyContinue
    if ($out) { $out | ForEach-Object { Write-Host $_ } }
    if ($j.State -ne "Completed") {
        if ($softFail -contains $j.Name) {
            Write-Host "[WARN] $($j.Name) failed (optional)" -ForegroundColor Yellow
        } else {
            $fail += $j.Name
            Write-Host "[FAIL] $($j.Name)" -ForegroundColor Red
        }
    } else {
        Write-Host "[OK] $($j.Name)" -ForegroundColor Green
    }
    Remove-Job -Job $j -Force -ErrorAction SilentlyContinue
}

Write-Host ">> lens_hardening (post-parallel, avoids artifact races)" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-LensParallelHardening_v1.ps1 -SkipTelegram
if ($LASTEXITCODE -ne 0) { $fail += "lens_hardening" }

& $py scripts/logos_oos_gate_promote_v1.py 2>$null | Out-Null

$oos120 = Join-Path $WorkspaceRoot "docs\final\artifacts\prophecy_logos_revalidation_oos_gate_120d_latest.json"
$oosLatest = Join-Path $WorkspaceRoot "docs\final\artifacts\prophecy_logos_revalidation_oos_gate_latest.json"
if (Test-Path -LiteralPath $oos120) {
    $g120 = Get-Content -LiteralPath $oos120 -Raw -Encoding UTF8 | ConvertFrom-Json
    $gNow = $null
    if (Test-Path -LiteralPath $oosLatest) {
        $gNow = Get-Content -LiteralPath $oosLatest -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    if ($null -eq $gNow -or -not $gNow.gate.go) {
        if ($g120.gate.go) {
            Copy-Item -LiteralPath $oos120 -Destination $oosLatest -Force
            Write-Host "[restore] logos OOS gate <- 120d snapshot (go=true)" -ForegroundColor Yellow
        }
    }
}

& $py scripts/build_myeongni_lens_observation_report_v1.py
& $py scripts/build_prophecy_hit_rate_per_lens_bundle_v1.py
& $py scripts/build_lens_maturity_self_score_v1.py
if ($LASTEXITCODE -ne 0) { $fail += "maturity_refresh" }

$summary = @{
    schema = "lens_advance_parallel_v1"
    finished_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    lanes_started = @($lanes | ForEach-Object { $_.Name })
    failed = $fail
    soft_fail_ok = $softFail
    btrack_10lane_report = "reports/btrack_parallel_10lane_v1_latest.json"
    maturity = "reports/lens_maturity_self_score_v1_latest.json"
}
$summaryPath = Join-Path $WorkspaceRoot "reports\lens_advance_parallel_latest.json"
$summary | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $summaryPath -Encoding UTF8
Write-Host "WROTE: $summaryPath"

if ($SendTelegram -and $fail.Count -eq 0) {
    & $py scripts/send_telegram_four_lens_reports_v1.py --force
    if ($LASTEXITCODE -ne 0) { $fail += "telegram" }
}

if ($fail.Count -gt 0) {
    Write-Host "[DONE] failed: $($fail -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "[DONE] all parallel lanes OK" -ForegroundColor Green
exit 0
