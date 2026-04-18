# Daily B-Track: build OHLCV score JSON + price-mode hit-rate eval + overlay ablation spike (unless -SkipOverlaySpike).
# Does NOT train models, promote canonical weights, or touch live trading.
#
# Prerequisites: py on PATH; KOSPI CSV at research/market_data/kospi_daily_external_yf.csv;
# hypothesis at docs/final/artifacts/btrack_hypothesis_prophecy_latest.json (from daily chain or stub).
#
# Optional env: MKM_BTC_DAILY_CSV (path to BTC daily CSV), MKM_PROPHECY_PROXY_REGISTRY_GLOB (proxy eval).
#
# Example (Task Scheduler):
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\run_daily_prophecy_eval_and_report.ps1" -IncludeDatedArchive
# Overlay ablation spike runs after eval by default; pass -SkipOverlaySpike for a faster pass.

param(
    [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [int]$RecentTradingDays = 1,
    [switch]$SkipBuildScore,
    [string]$BtcCsvPath = $env:MKM_BTC_DAILY_CSV,
    [double]$LowHitRateWarningThreshold = 0.5,
    [switch]$FailOnLowHitRate,
    [switch]$IncludeDatedArchive,
    [switch]$IncludeProxyEval,
    [string]$ProxyRegistryGlob = $env:MKM_PROPHECY_PROXY_REGISTRY_GLOB,
    [switch]$SkipOverlaySpike
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$evalScript = Join-Path $WorkspaceRoot "scripts\eval_prophecy_hit_rate_v1.py"
$hypoScript = Join-Path $WorkspaceRoot "scripts\generate_btrack_hypothesis_prophecy_v1.py"
if (-not (Test-Path -LiteralPath $evalScript)) {
    throw "Missing required script: $evalScript"
}
if (-not (Test-Path -LiteralPath $hypoScript)) {
    throw "Missing required script: $hypoScript"
}

$artifactsDir = Join-Path $WorkspaceRoot "docs\final\artifacts"
$scoreOut = Join-Path $artifactsDir "btrack_prophecy_score_latest.json"
$evalOut = Join-Path $artifactsDir "prophecy_hit_rate_eval_latest.json"
$reportsDir = Join-Path $WorkspaceRoot "reports"
$logPath = Join-Path $reportsDir "prophecy_daily_eval_log.jsonl"

if (-not $SkipBuildScore) {
    $buildArgs = @("scripts\build_btrack_prophecy_score_from_ohlcv.py")
    if ($RecentTradingDays -gt 1) {
        $buildArgs += @("--recent-trading-days", "$RecentTradingDays")
    }
    if ($BtcCsvPath -and (Test-Path -LiteralPath $BtcCsvPath)) {
        $buildArgs += @("--btc-csv", $BtcCsvPath)
    }
    Write-Host "==> build_btrack_prophecy_score_from_ohlcv.py"
    & py @buildArgs
    if ($LASTEXITCODE -ne 0) {
        throw "build_btrack_prophecy_score_from_ohlcv.py exit $LASTEXITCODE"
    }
}

Write-Host "==> eval_prophecy_hit_rate_v1.py (price)"
& py scripts\eval_prophecy_hit_rate_v1.py --run-mode price --score-json $scoreOut
if ($LASTEXITCODE -ne 0) {
    throw "eval_prophecy_hit_rate_v1.py (price) exit $LASTEXITCODE"
}

if ($IncludeProxyEval) {
    $proxyOut = Join-Path $artifactsDir "prophecy_hit_rate_eval_proxy_latest.json"
    $proxyArgs = @(
        "scripts\eval_prophecy_hit_rate_v1.py",
        "--run-mode", "proxy",
        "--output", $proxyOut
    )
    if ($ProxyRegistryGlob) {
        $proxyArgs += @("--registry-glob", $ProxyRegistryGlob)
    }
    Write-Host "==> eval_prophecy_hit_rate_v1.py (proxy)"
    & py @proxyArgs
    if ($LASTEXITCODE -ne 0) {
        throw "eval_prophecy_hit_rate_v1.py (proxy) exit $LASTEXITCODE"
    }
}

$overlaySpikeRan = $false
if (-not $SkipOverlaySpike) {
    $spikeScript = Join-Path $WorkspaceRoot "scripts\run_prophecy_restoration_spike.py"
    if (-not (Test-Path -LiteralPath $spikeScript)) {
        Write-Warning "Overlay spike skipped: missing $spikeScript"
    }
    else {
        Write-Host "==> run_prophecy_restoration_spike.py"
        & py $spikeScript
        if ($LASTEXITCODE -ne 0) {
            throw "run_prophecy_restoration_spike.py exit $LASTEXITCODE"
        }
        $overlaySpikeRan = $true
    }
}

if ($IncludeDatedArchive) {
    $d = Get-Date -Format "yyyy-MM-dd"
    if (Test-Path -LiteralPath $scoreOut) {
        Copy-Item -LiteralPath $scoreOut -Destination (Join-Path $artifactsDir "btrack_prophecy_score_$d.json") -Force
    }
    if (Test-Path -LiteralPath $evalOut) {
        Copy-Item -LiteralPath $evalOut -Destination (Join-Path $artifactsDir "prophecy_hit_rate_eval_$d.json") -Force
    }
}

$hit = $null
$n = 0
$status = "unknown"
if (Test-Path -LiteralPath $evalOut) {
    $raw = Get-Content -LiteralPath $evalOut -Raw -Encoding UTF8
    $j = $raw | ConvertFrom-Json
    if ($null -ne $j.metrics) {
        $hit = $j.metrics.price_directional_hit_rate
        $n = [int]$j.metrics.n_evaluated
    }
    $status = [string]$j.status
}

if (-not (Test-Path -LiteralPath $reportsDir)) {
    New-Item -ItemType Directory -Path $reportsDir -Force | Out-Null
}
$logObj = [ordered]@{
    ts_utc                     = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    pipeline                   = "run_daily_prophecy_eval_and_report.ps1"
    eval_status                = $status
    n_evaluated                = $n
    price_directional_hit_rate = $hit
    low_hit_threshold          = $LowHitRateWarningThreshold
    overlay_spike_ran          = $overlaySpikeRan
}
($logObj | ConvertTo-Json -Compress) | Add-Content -LiteralPath $logPath -Encoding UTF8

$warnLow = $false
if (($null -ne $hit) -and ($n -gt 0) -and ([double]$hit -lt $LowHitRateWarningThreshold)) {
    $warnLow = $true
    Write-Warning "Prophecy price hit rate $hit below threshold $LowHitRateWarningThreshold (n=$n). B-Track observability only; no canonical model change."
}

if ($FailOnLowHitRate -and $warnLow) {
    exit 2
}

Write-Host "OK: Daily prophecy eval finished. Latest: $evalOut Log: $logPath"
