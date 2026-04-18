# Daily B-Track: build OHLCV score JSON + price-mode hit-rate eval.
# Optional -IncludeOverlaySpike: refreshes prophecy_restoration_spike_latest.json (threshold per script default / sweep policy).
# Optional -IncludeShadowPanelEval: writes prophecy_shadow_panel_eval_v1_latest.json (B-track measurement lanes; not live routing).
#   -ShadowPanelMode all | walkforward_aggregate: runs run_prophecy_per_date_combo_walkforward_v1.py first so walk-forward JSON is fresh, then shadow eval.
#   Use -ShadowPanelMode instrument_combo_best for a lighter single-lane eval; or set MKM_PROPHECY_SHADOW_PANEL_MODE.
# Does NOT train models, promote canonical weights, or touch live trading.
#
# Prerequisites: py on PATH; KOSPI CSV at research/market_data/kospi_daily_external_yf.csv;
# hypothesis at docs/final/artifacts/btrack_hypothesis_prophecy_latest.json (from daily chain or stub).
#
# Optional env: MKM_BTC_DAILY_CSV (path to BTC daily CSV), MKM_PROPHECY_PROXY_REGISTRY_GLOB (proxy eval),
#   MKM_PROPHECY_SHADOW_PANEL_MODE (both | all | instrument_combo_best | per_date_lens_holdout_best | walkforward_aggregate) when -ShadowPanelMode omitted,
#   MKM_PROPHECY_WALKFORWARD_N_FOLDS (integer) passed to walk-forward script when shadow mode is all or walkforward_aggregate.
#
# Example (Task Scheduler):
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\run_daily_prophecy_eval_and_report.ps1" -IncludeDatedArchive

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
    # After score+eval: refresh prophecy_restoration_spike_latest.json (default overlay threshold from script).
    [switch]$IncludeOverlaySpike,
    # After score+eval: shadow panel lanes vs sweep/holdout artifacts (measurement-only).
    [switch]$IncludeShadowPanelEval,
    # Shadow eval mode (Python --shadow-mode). Omit to use env MKM_PROPHECY_SHADOW_PANEL_MODE or both.
    [string]$ShadowPanelMode = ""
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$evalScript = Join-Path $WorkspaceRoot "scripts\eval_prophecy_hit_rate_v1.py"
$shadowPanelScript = Join-Path $WorkspaceRoot "scripts\eval_prophecy_shadow_panel_v1.py"
$walkforwardScript = Join-Path $WorkspaceRoot "scripts\run_prophecy_per_date_combo_walkforward_v1.py"
$instrumentWalkforwardScript = Join-Path $WorkspaceRoot "scripts\run_prophecy_instrument_combo_walkforward_v1.py"
$hypoScript = Join-Path $WorkspaceRoot "scripts\generate_btrack_hypothesis_prophecy_v1.py"
if (-not (Test-Path -LiteralPath $evalScript)) {
    throw "Missing required script: $evalScript"
}
if (-not (Test-Path -LiteralPath $hypoScript)) {
    throw "Missing required script: $hypoScript"
}
if ($IncludeShadowPanelEval -and -not (Test-Path -LiteralPath $shadowPanelScript)) {
    throw "Missing required script: $shadowPanelScript"
}

$artifactsDir = Join-Path $WorkspaceRoot "docs\final\artifacts"
$scoreOut = Join-Path $artifactsDir "btrack_prophecy_score_latest.json"
$evalOut = Join-Path $artifactsDir "prophecy_hit_rate_eval_latest.json"
$shadowPanelOut = Join-Path $artifactsDir "prophecy_shadow_panel_eval_v1_latest.json"
$walkforwardOut = Join-Path $artifactsDir "prophecy_per_date_combo_walkforward_v1_latest.json"
$instrumentWalkforwardOut = Join-Path $artifactsDir "prophecy_instrument_combo_walkforward_v1_latest.json"
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

$shadowModeLogged = $null
$RegenWalkforwardThisRun = $false
$RegenInstrumentWfThisRun = $false
if ($IncludeShadowPanelEval) {
    $validShadowModes = @("both", "all", "instrument_combo_best", "per_date_lens_holdout_best", "walkforward_aggregate")
    $shadowModeResolved = if ($PSBoundParameters.ContainsKey("ShadowPanelMode") -and $ShadowPanelMode.Trim().Length -gt 0) {
        $ShadowPanelMode.Trim()
    }
    elseif ($env:MKM_PROPHECY_SHADOW_PANEL_MODE -and $env:MKM_PROPHECY_SHADOW_PANEL_MODE.Trim().Length -gt 0) {
        $env:MKM_PROPHECY_SHADOW_PANEL_MODE.Trim()
    }
    else {
        "both"
    }
    $shadowModeLogged = $shadowModeResolved
    if ($validShadowModes -notcontains $shadowModeResolved) {
        throw "Invalid ShadowPanelMode '$shadowModeResolved'. Use: $($validShadowModes -join ', ')"
    }
    if (($shadowModeResolved -eq "all" -or $shadowModeResolved -eq "walkforward_aggregate") -and -not (Test-Path -LiteralPath $walkforwardScript)) {
        throw "Missing required script: $walkforwardScript"
    }
    $kospiCsvDefault = Join-Path $WorkspaceRoot "research\market_data\kospi_daily_external_yf.csv"
    $btcCsvDefault = Join-Path $WorkspaceRoot "research\market_data\btc_daily_external_yf.csv"
    if ($shadowModeResolved -eq "all" -or $shadowModeResolved -eq "walkforward_aggregate") {
        $wfArgs = @(
            "scripts\run_prophecy_per_date_combo_walkforward_v1.py",
            "--score-json", $scoreOut,
            "--output", $walkforwardOut
        )
        if ($BtcCsvPath -and (Test-Path -LiteralPath $BtcCsvPath)) {
            $wfArgs += @("--btc-csv", $BtcCsvPath)
        }
        elseif (Test-Path -LiteralPath $btcCsvDefault) {
            $wfArgs += @("--btc-csv", $btcCsvDefault)
        }
        if (Test-Path -LiteralPath $kospiCsvDefault) {
            $wfArgs += @("--kospi-csv", $kospiCsvDefault)
        }
        if ($env:MKM_PROPHECY_WALKFORWARD_N_FOLDS -and $env:MKM_PROPHECY_WALKFORWARD_N_FOLDS.Trim().Length -gt 0) {
            $wfArgs += @("--n-folds", $env:MKM_PROPHECY_WALKFORWARD_N_FOLDS.Trim())
        }
        Write-Host "==> run_prophecy_per_date_combo_walkforward_v1.py (before shadow; mode=$shadowModeResolved)"
        & py @wfArgs
        if ($LASTEXITCODE -ne 0) {
            throw "run_prophecy_per_date_combo_walkforward_v1.py exit $LASTEXITCODE"
        }
        $RegenWalkforwardThisRun = $true
        if (Test-Path -LiteralPath $instrumentWalkforwardScript) {
            $instWfArgs = @(
                "scripts\run_prophecy_instrument_combo_walkforward_v1.py",
                "--score-json", $scoreOut,
                "--output", $instrumentWalkforwardOut
            )
            if ($BtcCsvPath -and (Test-Path -LiteralPath $BtcCsvPath)) {
                $instWfArgs += @("--btc-csv", $BtcCsvPath)
            }
            elseif (Test-Path -LiteralPath $btcCsvDefault) {
                $instWfArgs += @("--btc-csv", $btcCsvDefault)
            }
            if (Test-Path -LiteralPath $kospiCsvDefault) {
                $instWfArgs += @("--kospi-csv", $kospiCsvDefault)
            }
            if ($env:MKM_PROPHECY_WALKFORWARD_N_FOLDS -and $env:MKM_PROPHECY_WALKFORWARD_N_FOLDS.Trim().Length -gt 0) {
                $instWfArgs += @("--n-folds", $env:MKM_PROPHECY_WALKFORWARD_N_FOLDS.Trim())
            }
            Write-Host "==> run_prophecy_instrument_combo_walkforward_v1.py (before shadow)"
            & py @instWfArgs
            if ($LASTEXITCODE -eq 0) {
                $RegenInstrumentWfThisRun = $true
            }
            else {
                Write-Warning "Instrument walk-forward failed (exit $LASTEXITCODE). Rebuild score with KOSPI+BTC per eval_date and --btc-csv; promotion gates need both tracks."
            }
        }
    }
    $shadowArgs = @(
        "scripts\eval_prophecy_shadow_panel_v1.py",
        "--score-json", $scoreOut,
        "--shadow-mode", $shadowModeResolved,
        "--output", $shadowPanelOut
    )
    if ($BtcCsvPath -and (Test-Path -LiteralPath $BtcCsvPath)) {
        $shadowArgs += @("--btc-csv", $BtcCsvPath)
    }
    elseif (Test-Path -LiteralPath $btcCsvDefault) {
        $shadowArgs += @("--btc-csv", $btcCsvDefault)
    }
    if (Test-Path -LiteralPath $kospiCsvDefault) {
        $shadowArgs += @("--kospi-csv", $kospiCsvDefault)
    }
    if ($RegenWalkforwardThisRun) {
        $shadowArgs += @("--walkforward-json", $walkforwardOut)
    }
    Write-Host "==> eval_prophecy_shadow_panel_v1.py (--shadow-mode $shadowModeResolved)"
    & py @shadowArgs
    if ($LASTEXITCODE -ne 0) {
        throw "eval_prophecy_shadow_panel_v1.py exit $LASTEXITCODE"
    }
}

if ($IncludeOverlaySpike) {
    Write-Host "==> run_prophecy_restoration_spike.py"
    & py scripts\run_prophecy_restoration_spike.py
    if ($LASTEXITCODE -ne 0) {
        throw "run_prophecy_restoration_spike.py exit $LASTEXITCODE"
    }
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

if ($IncludeDatedArchive) {
    $d = Get-Date -Format "yyyy-MM-dd"
    if (Test-Path -LiteralPath $scoreOut) {
        Copy-Item -LiteralPath $scoreOut -Destination (Join-Path $artifactsDir "btrack_prophecy_score_$d.json") -Force
    }
    if (Test-Path -LiteralPath $evalOut) {
        Copy-Item -LiteralPath $evalOut -Destination (Join-Path $artifactsDir "prophecy_hit_rate_eval_$d.json") -Force
    }
    if ($IncludeShadowPanelEval -and (Test-Path -LiteralPath $shadowPanelOut)) {
        Copy-Item -LiteralPath $shadowPanelOut -Destination (Join-Path $artifactsDir "prophecy_shadow_panel_eval_v1_$d.json") -Force
    }
    if ($RegenWalkforwardThisRun -and (Test-Path -LiteralPath $walkforwardOut)) {
        Copy-Item -LiteralPath $walkforwardOut -Destination (Join-Path $artifactsDir "prophecy_per_date_combo_walkforward_v1_$d.json") -Force
    }
    if ($RegenInstrumentWfThisRun -and (Test-Path -LiteralPath $instrumentWalkforwardOut)) {
        Copy-Item -LiteralPath $instrumentWalkforwardOut -Destination (Join-Path $artifactsDir "prophecy_instrument_combo_walkforward_v1_$d.json") -Force
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
$shadowHit = $null
$shadowN = $null
$shadowLanesLog = $null
if ($IncludeShadowPanelEval -and (Test-Path -LiteralPath $shadowPanelOut)) {
    $sj = Get-Content -LiteralPath $shadowPanelOut -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($null -ne $sj.lanes) {
        $lane0 = $sj.lanes | Select-Object -First 1
        if ($null -ne $lane0.metrics_all) {
            $shadowHit = $lane0.metrics_all.price_directional_hit_rate
            $shadowN = [int]$lane0.metrics_all.n_evaluated
        }
        $summaries = New-Object System.Collections.ArrayList
        foreach ($lane in @($sj.lanes)) {
            $mid = $lane.lane_id
            $m = $lane.metrics_all
            if ($null -ne $m) {
                [void]$summaries.Add(
                    [ordered]@{
                        lane_id                    = [string]$mid
                        lane_kind                  = "row_panel"
                        price_directional_hit_rate = $m.price_directional_hit_rate
                        n_evaluated                = [int]$m.n_evaluated
                        delta_vs_baseline          = $lane.delta_vs_baseline
                    }
                )
            }
            elseif ($lane.lane_kind -eq "fold_aggregate" -and $null -ne $lane.walkforward_aggregate) {
                $agg = $lane.walkforward_aggregate
                [void]$summaries.Add(
                    [ordered]@{
                        lane_id                    = [string]$mid
                        lane_kind                  = "fold_aggregate"
                        mean_test_accuracy         = $agg.mean_test_accuracy
                        stdev_test_accuracy        = $agg.stdev_test_accuracy
                        walkforward_fold_count     = [int]$lane.walkforward_fold_count
                        fraction_beats_always_bull = $agg.fraction_test_beats_always_bull
                    }
                )
            }
        }
        if ($summaries.Count -gt 0) {
            $shadowLanesLog = @($summaries.ToArray())
        }
    }
}

$logObj = [ordered]@{
    ts_utc                     = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    pipeline                   = "run_daily_prophecy_eval_and_report.ps1"
    eval_status                = $status
    n_evaluated                = $n
    price_directional_hit_rate = $hit
    low_hit_threshold          = $LowHitRateWarningThreshold
    shadow_panel_eval_path     = $(if ($IncludeShadowPanelEval) { $shadowPanelOut } else { $null })
    shadow_panel_mode          = $shadowModeLogged
    shadow_lane0_hit_rate      = $shadowHit
    shadow_lane0_n_evaluated   = $shadowN
    shadow_lanes               = $shadowLanesLog
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
