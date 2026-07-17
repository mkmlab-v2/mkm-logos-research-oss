# Daily B-Track: build OHLCV score JSON + price-mode hit-rate eval.
# Optional -IncludeOverlaySpike: refreshes prophecy_restoration_spike_latest.json (threshold per script default / sweep policy).
# Optional -IncludeShadowPanelEval: writes prophecy_shadow_panel_eval_v1_latest.json (B-track measurement lanes; not live routing).
#   -ShadowPanelMode all | walkforward_aggregate: runs run_prophecy_per_date_combo_walkforward_v1.py first (target-instrument=btc) so walk-forward JSON is fresh, then shadow eval.
#   Use -ShadowPanelMode instrument_combo_best for a lighter single-lane eval; or set MKM_PROPHECY_SHADOW_PANEL_MODE.
# Does NOT train models, promote canonical weights, or touch live trading.
#
# Prerequisites: py on PATH; KOSPI CSV at research/market_data/kospi_daily_external_yf.csv;
# hypothesis at docs/final/artifacts/btrack_hypothesis_prophecy_latest.json (from daily chain or stub).
#
# Optional env: MKM_BTC_DAILY_CSV (path to BTC daily CSV), MKM_PROPHECY_PROXY_REGISTRY_GLOB (proxy eval),
#   MKM_PROPHECY_SHADOW_PANEL_MODE (both | all | instrument_combo_best | per_date_lens_holdout_best | walkforward_aggregate) when -ShadowPanelMode omitted,
#   MKM_PROPHECY_WALKFORWARD_N_FOLDS (integer) passed to walk-forward script when shadow mode is all or walkforward_aggregate.
# Optional -IncludeCrossLensRagFusion: refreshes cross_lens_rag_fusion_latest.json + three_lens_sphere_envelope (Telegram advanced I-c/I-d).
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
    [switch]$FailOnRuntimeHealthRed,
    [switch]$IncludeDatedArchive,
    [switch]$IncludeProxyEval,
    [string]$ProxyRegistryGlob = $env:MKM_PROPHECY_PROXY_REGISTRY_GLOB,
    # After score+eval: refresh prophecy_restoration_spike_latest.json (default overlay threshold from script).
    [switch]$IncludeOverlaySpike,
    # After score+eval: shadow panel lanes vs sweep/holdout artifacts (measurement-only).
    [switch]$IncludeShadowPanelEval,
    # Shadow eval mode (Python --shadow-mode). Omit to use env MKM_PROPHECY_SHADOW_PANEL_MODE or both.
    [string]$ShadowPanelMode = "",
    [switch]$SkipHypothesisRefresh,
    [switch]$SkipTrinityEvolution,
    [switch]$SkipRiskProfileSync,
    [switch]$DisableAutoTrinitySafetyGate,
    [switch]$EnableBtcPromotionAutoExecute,
    [string]$BtcPromotionExecuteCommand = "",
    [int]$TrinitySafetyWindow = 30,
    [int]$TrinitySafetyConsecutiveThreshold = 3,
    [int]$TrinitySafetyWindowKospi = 0,
    [int]$TrinitySafetyConsecutiveThresholdKospi = 0,
    [int]$TrinitySafetyWindowBtc = 0,
    [int]$TrinitySafetyConsecutiveThresholdBtc = 0,
    [switch]$SkipRuntimeHealthGuard,
    # Operation Mode B: live ON + prophecy gates not passed -> amber (not red GATE_LIVE_CONFLICT).
    [switch]$OperationModeBShadow,
    # After eval: refresh cross_lens_rag_fusion + three_lens_sphere for 08:28 Telegram I-c/I-d.
    [switch]$IncludeCrossLensRagFusion,
    [switch]$SkipCrossLensRagFusion,
    # After score+eval: dual-leg brief + internal KOSPI morning onepager (08:28 prophecy TG).
    [switch]$IncludeKospiMorningBrief,
    [switch]$SkipKospiMorningBrief
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$btcCsvDefault = Join-Path $WorkspaceRoot "research\market_data\btc_daily_external_yf.csv"
if (-not $BtcCsvPath -and (Test-Path -LiteralPath $btcCsvDefault)) {
    $BtcCsvPath = $btcCsvDefault
}

$evalScript = Join-Path $WorkspaceRoot "scripts\eval_prophecy_hit_rate_v1.py"
$shadowPanelScript = Join-Path $WorkspaceRoot "scripts\eval_prophecy_shadow_panel_v1.py"
$walkforwardScript = Join-Path $WorkspaceRoot "scripts\run_prophecy_per_date_combo_walkforward_v1.py"
$instrumentWalkforwardScript = Join-Path $WorkspaceRoot "scripts\run_prophecy_instrument_combo_walkforward_v1.py"
$hypoScript = Join-Path $WorkspaceRoot "scripts\generate_btrack_hypothesis_prophecy_v1.py"
$runtimeHealthScript = Join-Path $WorkspaceRoot "scripts\evaluate_prophecy_runtime_health_v1.py"
$trinityBuildScript = Join-Path $WorkspaceRoot "scripts\core\trinity_build_prediction.py"
$trinityDailyScoreScript = Join-Path $WorkspaceRoot "scripts\core\trinity_daily_scorer.py"
$trinityWeightTunerScript = Join-Path $WorkspaceRoot "scripts\core\trinity_weight_tuner.py"
$trinitySafetyGateScript = Join-Path $WorkspaceRoot "scripts\core\trinity_safety_gate.py"
$riskSyncScript = Join-Path $WorkspaceRoot "scripts\sync_fact_safe_risk_profile.py"
if (-not (Test-Path -LiteralPath $evalScript)) {
    throw "Missing required script: $evalScript"
}
if (-not (Test-Path -LiteralPath $hypoScript)) {
    throw "Missing required script: $hypoScript"
}

if (-not $SkipHypothesisRefresh) {
    Write-Host "==> generate_btrack_hypothesis_prophecy_v1.py (auto refresh; manual override guard)"
    & py "scripts\generate_btrack_hypothesis_prophecy_v1.py"
    if ($LASTEXITCODE -ne 0) {
        throw "generate_btrack_hypothesis_prophecy_v1.py exit $LASTEXITCODE"
    }
}
if ($IncludeShadowPanelEval -and -not (Test-Path -LiteralPath $shadowPanelScript)) {
    throw "Missing required script: $shadowPanelScript"
}

$artifactsDir = Join-Path $WorkspaceRoot "docs\final\artifacts"
$scoreOut = Join-Path $artifactsDir "btrack_prophecy_score_latest.json"
$evalOut = Join-Path $artifactsDir "prophecy_hit_rate_eval_daily_operational_latest.json"
$headlineEvalOut = Join-Path $artifactsDir "prophecy_hit_rate_eval_latest.json"
$shadowPanelOut = Join-Path $artifactsDir "prophecy_shadow_panel_eval_v1_latest.json"
$runtimeHealthOut = Join-Path $artifactsDir "prophecy_runtime_health_guard_latest.json"
$walkforwardOut = Join-Path $artifactsDir "prophecy_per_date_combo_walkforward_v1_latest.json"
$instrumentWalkforwardOut = Join-Path $artifactsDir "prophecy_instrument_combo_walkforward_v1_latest.json"
$reportsDir = Join-Path $WorkspaceRoot "reports"
$logPath = Join-Path $reportsDir "prophecy_daily_eval_log.jsonl"
$trinityPredictionOut = Join-Path $artifactsDir "trinity_3lens_prediction_latest.json"
$trinityDailyScoreOut = Join-Path $artifactsDir "trinity_daily_score_latest.json"
$trinityDailyScoreLog = Join-Path $artifactsDir "trinity_daily_score_log.jsonl"
$trinityWeightsOut = Join-Path $artifactsDir "trinity_lens_weights_latest.json"
$trinityWeightsKospiOut = Join-Path $artifactsDir "trinity_lens_weights_kospi_latest.json"
$trinityWeightsBtcOut = Join-Path $artifactsDir "trinity_lens_weights_btc_latest.json"
$trinitySafetyGateOut = Join-Path $artifactsDir "trinity_safety_gate_latest.json"
$trinitySafetyGateKospiOut = Join-Path $artifactsDir "trinity_safety_gate_kospi_latest.json"
$trinitySafetyGateBtcOut = Join-Path $artifactsDir "trinity_safety_gate_btc_latest.json"
$trinityPredictionBtcOut = Join-Path $artifactsDir "trinity_3lens_prediction_btc_latest.json"
$trinityDailyScoreBtcOut = Join-Path $artifactsDir "trinity_daily_score_btc_latest.json"
$trinityOpsSnapshotScript = Join-Path $WorkspaceRoot "scripts\core\trinity_build_ops_snapshot.py"
$trinityOpsSnapshotOut = Join-Path $artifactsDir "trinity_ops_snapshot_latest.json"
$trinityOpsAlertScript = Join-Path $WorkspaceRoot "scripts\core\trinity_ops_alert_rules.py"
$trinityOpsAlertOut = Join-Path $artifactsDir "trinity_ops_alerts_latest.json"
$trinityBtcPromotionGateScript = Join-Path $WorkspaceRoot "scripts\core\build_trinity_btc_promotion_gate_v1.py"
$trinityBtcPromotionGateOut = Join-Path $artifactsDir "trinity_btc_promotion_gate_latest.json"
$trinityBtcPromotionRecommendationScript = Join-Path $WorkspaceRoot "scripts\core\build_trinity_btc_promotion_recommendation_v1.py"
$trinityBtcPromotionRecommendationOut = Join-Path $artifactsDir "trinity_btc_promotion_recommendation_latest.json"
$trinityBtcPromotionExecutionScript = Join-Path $WorkspaceRoot "scripts\core\execute_trinity_btc_staging_promotion_v1.py"
$trinityBtcPromotionExecutionOut = Join-Path $artifactsDir "trinity_btc_promotion_execution_latest.json"
$btcPromotionVpsRunner = Join-Path $WorkspaceRoot "scripts\execute_btc_promotion_on_vps_v1.ps1"

if (-not $SkipBuildScore) {
    $buildArgs = @("scripts\build_btrack_prophecy_score_from_ohlcv.py")
    if ($RecentTradingDays -gt 1) {
        $buildArgs += @("--recent-trading-days", "$RecentTradingDays")
    }
    $kospiCsvDefault = Join-Path $WorkspaceRoot "research\market_data\kospi_daily_external_yf.csv"
    if ($BtcCsvPath -and (Test-Path -LiteralPath $BtcCsvPath)) {
        $buildArgs += @("--btc-csv", $BtcCsvPath)
    }
    if ((Test-Path -LiteralPath $kospiCsvDefault) -and $BtcCsvPath -and (Test-Path -LiteralPath $BtcCsvPath)) {
        $buildArgs += @("--force-dual-leg-panel")
    }
    Write-Host "==> build_btrack_prophecy_score_from_ohlcv.py"
    & py @buildArgs
    if ($LASTEXITCODE -ne 0) {
        throw "build_btrack_prophecy_score_from_ohlcv.py exit $LASTEXITCODE"
    }
}

Write-Host "==> eval_prophecy_hit_rate_v1.py (price -> daily operational; headline KPI untouched)"
& py scripts\eval_prophecy_hit_rate_v1.py --run-mode price --score-json $scoreOut --output $evalOut
if ($LASTEXITCODE -ne 0) {
    throw "eval_prophecy_hit_rate_v1.py (price) exit $LASTEXITCODE"
}

$runtimeHealthStatus = $null
$runtimeHealthShouldPauseTrading = $null
if (-not $SkipRuntimeHealthGuard -and (Test-Path -LiteralPath $runtimeHealthScript)) {
    Write-Host "==> evaluate_prophecy_runtime_health_v1.py"
    $rhArgs = @($runtimeHealthScript, "--output", $runtimeHealthOut)
    if ($OperationModeBShadow) { $rhArgs += "--operation-mode-b-shadow" }
    & py @rhArgs
    if ($LASTEXITCODE -ne 0) {
        throw "evaluate_prophecy_runtime_health_v1.py exit $LASTEXITCODE"
    }
    if (Test-Path -LiteralPath $runtimeHealthOut) {
        $rh = Get-Content -LiteralPath $runtimeHealthOut -Raw -Encoding UTF8 | ConvertFrom-Json
        $runtimeHealthStatus = [string]$rh.status
        $runtimeHealthShouldPauseTrading = [bool]$rh.should_pause_trading
        if ($runtimeHealthStatus -eq "red") {
            Write-Warning "Runtime health guard RED: prophecy/live boundary is unsafe. Keep trading paused until fixed."
        }
    }
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
            "--target-instrument", "btc",
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
    if (Test-Path -LiteralPath $trinityPredictionOut) {
        Copy-Item -LiteralPath $trinityPredictionOut -Destination (Join-Path $artifactsDir "trinity_3lens_prediction_$d.json") -Force
    }
    if (Test-Path -LiteralPath $trinityDailyScoreOut) {
        Copy-Item -LiteralPath $trinityDailyScoreOut -Destination (Join-Path $artifactsDir "trinity_daily_score_$d.json") -Force
    }
    if (Test-Path -LiteralPath $trinityWeightsOut) {
        Copy-Item -LiteralPath $trinityWeightsOut -Destination (Join-Path $artifactsDir "trinity_lens_weights_$d.json") -Force
    }
    if (Test-Path -LiteralPath $trinityWeightsKospiOut) {
        Copy-Item -LiteralPath $trinityWeightsKospiOut -Destination (Join-Path $artifactsDir "trinity_lens_weights_kospi_$d.json") -Force
    }
    if (Test-Path -LiteralPath $trinityWeightsBtcOut) {
        Copy-Item -LiteralPath $trinityWeightsBtcOut -Destination (Join-Path $artifactsDir "trinity_lens_weights_btc_$d.json") -Force
    }
    if (Test-Path -LiteralPath $trinityOpsSnapshotOut) {
        Copy-Item -LiteralPath $trinityOpsSnapshotOut -Destination (Join-Path $artifactsDir "trinity_ops_snapshot_$d.json") -Force
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

$trinityPredictionId = $null
$trinityBrier = $null
$trinityRegimeDecision = $null
$trinityWeightMode = $null
$trinityFailSafeTriggered = $null
$trinityMeanBrier = $null
$trinityFailRate = $null
$trinityWB = $null
$trinityWM = $null
$trinityWS = $null
$trinityAutoSafetyDecision = $null
$trinityAutoSafetyActive = $false
$trinityAutoSafetyDecisionKospi = $null
$trinityAutoSafetyActiveKospi = $false
$trinityAutoSafetyDecisionBtc = $null
$trinityAutoSafetyActiveBtc = $false
$trinityBtcPredictionId = $null
$trinityBtcBrier = $null
$trinityBtcRegimeDecision = $null
$trinityFailSafeTriggeredBtc = $null
if (-not $SkipRiskProfileSync) {
    if (-not (Test-Path -LiteralPath $riskSyncScript)) {
        throw "Missing required script: $riskSyncScript"
    }
}
if (-not $SkipTrinityEvolution -and -not $DisableAutoTrinitySafetyGate) {
    $safetyWindowKospi = if ($TrinitySafetyWindowKospi -gt 0) { $TrinitySafetyWindowKospi } else { $TrinitySafetyWindow }
    $safetyThresholdKospi = if ($TrinitySafetyConsecutiveThresholdKospi -gt 0) { $TrinitySafetyConsecutiveThresholdKospi } else { $TrinitySafetyConsecutiveThreshold }
    $safetyWindowBtc = if ($TrinitySafetyWindowBtc -gt 0) { $TrinitySafetyWindowBtc } else { $TrinitySafetyWindow }
    $safetyThresholdBtc = if ($TrinitySafetyConsecutiveThresholdBtc -gt 0) { $TrinitySafetyConsecutiveThresholdBtc } else { $TrinitySafetyConsecutiveThreshold }
    if (Test-Path -LiteralPath $trinitySafetyGateScript) {
        & py $trinitySafetyGateScript --log-path $logPath --output $trinitySafetyGateOut --window $TrinitySafetyWindow --consecutive-threshold $TrinitySafetyConsecutiveThreshold
        if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $trinitySafetyGateOut)) {
            $sg = Get-Content -LiteralPath $trinitySafetyGateOut -Raw -Encoding UTF8 | ConvertFrom-Json
            $trinityAutoSafetyDecision = [string]$sg.decision
        }
        & py $trinitySafetyGateScript --log-path $logPath --bool-field "trinity_fail_safe_triggered_kospi" --output $trinitySafetyGateKospiOut --window $safetyWindowKospi --consecutive-threshold $safetyThresholdKospi
        if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $trinitySafetyGateKospiOut)) {
            $sgk = Get-Content -LiteralPath $trinitySafetyGateKospiOut -Raw -Encoding UTF8 | ConvertFrom-Json
            $trinityAutoSafetyDecisionKospi = [string]$sgk.decision
            if ($sgk.enforce_skip_trinity_evolution -eq $true) {
                $trinityAutoSafetyActiveKospi = $true
                Write-Warning "Auto safety gate (KOSPI) active: skip KOSPI trinity evolution for this run."
            }
        }
        & py $trinitySafetyGateScript --log-path $logPath --bool-field "trinity_fail_safe_triggered_btc" --output $trinitySafetyGateBtcOut --window $safetyWindowBtc --consecutive-threshold $safetyThresholdBtc
        if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $trinitySafetyGateBtcOut)) {
            $sgb = Get-Content -LiteralPath $trinitySafetyGateBtcOut -Raw -Encoding UTF8 | ConvertFrom-Json
            $trinityAutoSafetyDecisionBtc = [string]$sgb.decision
            if ($sgb.enforce_skip_trinity_evolution -eq $true) {
                $trinityAutoSafetyActiveBtc = $true
                Write-Warning "Auto safety gate (BTC) active: skip BTC trinity evolution for this run."
            }
        }
        $trinityAutoSafetyActive = ($trinityAutoSafetyActiveKospi -or $trinityAutoSafetyActiveBtc)
    }
}
if (-not $SkipTrinityEvolution) {
    $trinityScriptsOk = @(
        (Test-Path -LiteralPath $trinityBuildScript),
        (Test-Path -LiteralPath $trinityDailyScoreScript),
        (Test-Path -LiteralPath $trinityWeightTunerScript)
    ) -notcontains $false
    if (-not $trinityScriptsOk) {
        Write-Warning "Trinity evolution scripts missing under scripts/core/; skipping trinity block (use -SkipTrinityEvolution to silence)."
        $SkipTrinityEvolution = $true
    }
}
if (-not $SkipTrinityEvolution) {
    if (Test-Path -LiteralPath $scoreOut) {
        $scoreJson = Get-Content -LiteralPath $scoreOut -Raw -Encoding UTF8 | ConvertFrom-Json
        $lastKospi = $null
        if ($null -ne $scoreJson.rows) {
            $lastKospi = @($scoreJson.rows | Where-Object { $_.instrument -eq "kospi" } | Select-Object -Last 1)
        }
        if (($lastKospi.Count -gt 0 -and $null -ne $lastKospi[0].daily_return) -and -not $trinityAutoSafetyActiveKospi) {
            $dailyReturnPct = [double]$lastKospi[0].daily_return * 100.0
            Write-Host "==> trinity_build_prediction.py"
            & py $trinityBuildScript --target "KOSPI_D1_RETURN_PCT" --horizon "D1" --output $trinityPredictionOut --weights-json $trinityWeightsKospiOut
            if ($LASTEXITCODE -ne 0) {
                throw "trinity_build_prediction.py exit $LASTEXITCODE"
            }
            Write-Host "==> trinity_daily_scorer.py"
            & py $trinityDailyScoreScript --prediction $trinityPredictionOut --realized-return-pct $dailyReturnPct --output $trinityDailyScoreOut --append-log $trinityDailyScoreLog
            if ($LASTEXITCODE -ne 0) {
                throw "trinity_daily_scorer.py exit $LASTEXITCODE"
            }
            Write-Host "==> trinity_weight_tuner.py"
            & py $trinityWeightTunerScript --score-log $trinityDailyScoreLog --target "KOSPI_D1_RETURN_PCT" --output $trinityWeightsKospiOut
            if ($LASTEXITCODE -ne 0) {
                throw "trinity_weight_tuner.py exit $LASTEXITCODE"
            }
            if (Test-Path -LiteralPath $trinityWeightsKospiOut) {
                Copy-Item -LiteralPath $trinityWeightsKospiOut -Destination $trinityWeightsOut -Force
            }
            if (Test-Path -LiteralPath $trinityPredictionOut) {
                $tp = Get-Content -LiteralPath $trinityPredictionOut -Raw -Encoding UTF8 | ConvertFrom-Json
                $trinityPredictionId = [string]$tp.prediction_id
            }
            if (Test-Path -LiteralPath $trinityDailyScoreOut) {
                $ts = Get-Content -LiteralPath $trinityDailyScoreOut -Raw -Encoding UTF8 | ConvertFrom-Json
                $trinityBrier = $ts.brier_score_3class
                $trinityRegimeDecision = [string]$ts.regime_decision
            }
            if (Test-Path -LiteralPath $trinityWeightsKospiOut) {
                $tw = Get-Content -LiteralPath $trinityWeightsKospiOut -Raw -Encoding UTF8 | ConvertFrom-Json
                $trinityWeightMode = [string]$tw.mode
                if ($null -ne $tw.stats) {
                    $trinityFailSafeTriggered = $tw.stats.fail_safe_triggered
                    $trinityMeanBrier = $tw.stats.mean_brier_score_3class
                    $trinityFailRate = $tw.stats.fail_rate
                }
                if ($null -ne $tw.weights) {
                    $trinityWB = $tw.weights.wB
                    $trinityWM = $tw.weights.wM
                    $trinityWS = $tw.weights.wS
                }
            }
        }
        elseif ($trinityAutoSafetyActiveKospi) {
            Write-Warning "Skip trinity evolution: auto safety gate is active for KOSPI target."
        }
        else {
            Write-Warning "Skip trinity evolution: no KOSPI daily_return row found in $scoreOut"
        }

        $btcCsvResolved = $null
        if ($BtcCsvPath -and (Test-Path -LiteralPath $BtcCsvPath)) {
            $btcCsvResolved = $BtcCsvPath
        }
        else {
            $btcCsvDefault = Join-Path $WorkspaceRoot "research\market_data\btc_daily_external_yf.csv"
            if (Test-Path -LiteralPath $btcCsvDefault) {
                $btcCsvResolved = $btcCsvDefault
            }
        }
        if ($btcCsvResolved -and -not $trinityAutoSafetyActiveBtc) {
            $btcDailyReturnPct = $null
            try {
                $btcRows = @(Import-Csv -LiteralPath $btcCsvResolved)
                if ($btcRows.Count -ge 2) {
                    $btcPrev = $btcRows[$btcRows.Count - 2]
                    $btcLast = $btcRows[$btcRows.Count - 1]
                    $prevCloseVal = [double]$btcPrev.Close
                    $closeVal = [double]$btcLast.Close
                    if ($prevCloseVal -ne 0) {
                        # Standard daily return basis: Prev Close -> Close
                        $btcDailyReturnPct = (($closeVal - $prevCloseVal) / $prevCloseVal) * 100.0
                    }
                }
            }
            catch {
                Write-Warning "BTC daily return parse failed from $btcCsvResolved : $($_.Exception.Message)"
            }
            if ($null -ne $btcDailyReturnPct) {
                Write-Host "==> trinity_build_prediction.py (BTC)"
                & py $trinityBuildScript --target "BTC_BINANCE_D1_RETURN_PCT" --horizon "D1" --output $trinityPredictionBtcOut --weights-json $trinityWeightsBtcOut
                if ($LASTEXITCODE -ne 0) {
                    throw "trinity_build_prediction.py (BTC) exit $LASTEXITCODE"
                }
                Write-Host "==> trinity_daily_scorer.py (BTC)"
                & py $trinityDailyScoreScript --prediction $trinityPredictionBtcOut --realized-return-pct $btcDailyReturnPct --output $trinityDailyScoreBtcOut --append-log $trinityDailyScoreLog
                if ($LASTEXITCODE -ne 0) {
                    throw "trinity_daily_scorer.py (BTC) exit $LASTEXITCODE"
                }
                Write-Host "==> trinity_weight_tuner.py (BTC)"
                & py $trinityWeightTunerScript --score-log $trinityDailyScoreLog --target "BTC_BINANCE_D1_RETURN_PCT" --output $trinityWeightsBtcOut
                if ($LASTEXITCODE -ne 0) {
                    throw "trinity_weight_tuner.py (BTC) exit $LASTEXITCODE"
                }
                if (Test-Path -LiteralPath $trinityWeightsBtcOut) {
                    $twb = Get-Content -LiteralPath $trinityWeightsBtcOut -Raw -Encoding UTF8 | ConvertFrom-Json
                    if ($null -ne $twb.stats) {
                        $trinityFailSafeTriggeredBtc = $twb.stats.fail_safe_triggered
                    }
                }
                if (Test-Path -LiteralPath $trinityPredictionBtcOut) {
                    $tpb = Get-Content -LiteralPath $trinityPredictionBtcOut -Raw -Encoding UTF8 | ConvertFrom-Json
                    $trinityBtcPredictionId = [string]$tpb.prediction_id
                }
                if (Test-Path -LiteralPath $trinityDailyScoreBtcOut) {
                    $tsb = Get-Content -LiteralPath $trinityDailyScoreBtcOut -Raw -Encoding UTF8 | ConvertFrom-Json
                    $trinityBtcBrier = $tsb.brier_score_3class
                    $trinityBtcRegimeDecision = [string]$tsb.regime_decision
                }
            }
            else {
                Write-Warning "Skip BTC trinity score: unable to derive daily return from $btcCsvResolved"
            }
        }
        elseif (-not $trinityAutoSafetyActiveBtc) {
            Write-Warning "Skip BTC trinity score: BTC CSV not found (MKM_BTC_DAILY_CSV or research/market_data/btc_daily_external_yf.csv)."
        }
        elseif ($trinityAutoSafetyActiveBtc) {
            Write-Warning "Skip BTC trinity score: auto safety gate is active for BTC target."
        }
    }
    else {
        Write-Warning "Skip trinity evolution: missing score JSON $scoreOut"
    }
}

$riskProfilePath = Join-Path $WorkspaceRoot "projects\bitcoin-trading\memory\v2\risk\risk_profile_fact_safe_latest.json"
if (-not $SkipRiskProfileSync) {
    Write-Host "==> sync_fact_safe_risk_profile.py (--repo-source + --allow-metadata-downgrade)"
    & py $riskSyncScript --repo-source --allow-metadata-downgrade
    if ($LASTEXITCODE -ne 0) {
        throw "sync_fact_safe_risk_profile.py exit $LASTEXITCODE"
    }
    $riskProfilePath = Join-Path $WorkspaceRoot "projects\bitcoin-trading\memory\v2\risk\risk_profile_fact_safe_latest.json"
}

if (Test-Path -LiteralPath $trinityOpsSnapshotScript) {
    if (Test-Path -LiteralPath $trinityBtcPromotionGateScript) {
        & py $trinityBtcPromotionGateScript `
            --score-log $trinityDailyScoreLog `
            --ops-snapshot $trinityOpsSnapshotOut `
            --window-days 14 `
            --output $trinityBtcPromotionGateOut
    }
    if (Test-Path -LiteralPath $trinityBtcPromotionRecommendationScript) {
        & py $trinityBtcPromotionRecommendationScript `
            --gate $trinityBtcPromotionGateOut `
            --output $trinityBtcPromotionRecommendationOut
    }
    if (Test-Path -LiteralPath $trinityBtcPromotionExecutionScript) {
        $resolvedPromotionCmd = $BtcPromotionExecuteCommand
        if ((-not $resolvedPromotionCmd -or $resolvedPromotionCmd.Trim().Length -eq 0) -and $env:MKM_BTC_PROMOTION_EXECUTE_COMMAND) {
            $resolvedPromotionCmd = [string]$env:MKM_BTC_PROMOTION_EXECUTE_COMMAND
        }
        $promoExecArgs = @(
            $trinityBtcPromotionExecutionScript,
            "--recommendation", $trinityBtcPromotionRecommendationOut,
            "--gate", $trinityBtcPromotionGateOut,
            "--output", $trinityBtcPromotionExecutionOut
        )
        if ($EnableBtcPromotionAutoExecute) {
            $promoExecArgs += "--confirm-execute"
            if ((-not $resolvedPromotionCmd -or $resolvedPromotionCmd.Trim().Length -eq 0) -and (Test-Path -LiteralPath $btcPromotionVpsRunner)) {
                $resolvedPromotionCmd = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$btcPromotionVpsRunner`""
            }
            if ($resolvedPromotionCmd -and $resolvedPromotionCmd.Trim().Length -gt 0) {
                $promoExecArgs += @("--execute-command", $resolvedPromotionCmd.Trim())
            }
        }
        & py @promoExecArgs
    }
    & py $trinityOpsSnapshotScript `
        --prediction-kospi $trinityPredictionOut `
        --score-kospi $trinityDailyScoreOut `
        --weights-kospi $trinityWeightsKospiOut `
        --prediction-btc $trinityPredictionBtcOut `
        --score-btc $trinityDailyScoreBtcOut `
        --weights-btc $trinityWeightsBtcOut `
        --safety-gate-kospi $trinitySafetyGateKospiOut `
        --safety-gate-btc $trinitySafetyGateBtcOut `
        --safety-gate-global $trinitySafetyGateOut `
        --btc-promotion-gate $trinityBtcPromotionGateOut `
        --btc-promotion-recommendation $trinityBtcPromotionRecommendationOut `
        --btc-promotion-execution $trinityBtcPromotionExecutionOut `
        --risk-profile $riskProfilePath `
        --output $trinityOpsSnapshotOut
}
if (Test-Path -LiteralPath $trinityOpsAlertScript) {
    & py $trinityOpsAlertScript `
        --snapshot $trinityOpsSnapshotOut `
        --daily-log $logPath `
        --output $trinityOpsAlertOut `
        --risk-sync-required
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
    trinity_prediction_id      = $trinityPredictionId
    trinity_brier_score_3class = $trinityBrier
    trinity_regime_decision    = $trinityRegimeDecision
    trinity_weight_mode        = $trinityWeightMode
    trinity_fail_safe_triggered= $trinityFailSafeTriggered
    trinity_fail_safe_triggered_kospi = $trinityFailSafeTriggered
    trinity_fail_safe_triggered_btc = $trinityFailSafeTriggeredBtc
    trinity_mean_brier         = $trinityMeanBrier
    trinity_fail_rate          = $trinityFailRate
    trinity_wB                 = $trinityWB
    trinity_wM                 = $trinityWM
    trinity_wS                 = $trinityWS
    trinity_auto_safety_decision = $trinityAutoSafetyDecision
    trinity_auto_safety_active = $trinityAutoSafetyActive
    trinity_auto_safety_decision_kospi = $trinityAutoSafetyDecisionKospi
    trinity_auto_safety_active_kospi = $trinityAutoSafetyActiveKospi
    trinity_auto_safety_decision_btc = $trinityAutoSafetyDecisionBtc
    trinity_auto_safety_active_btc = $trinityAutoSafetyActiveBtc
    trinity_auto_safety_window = $TrinitySafetyWindow
    trinity_auto_safety_consecutive_threshold = $TrinitySafetyConsecutiveThreshold
    trinity_auto_safety_window_kospi = $(if ($TrinitySafetyWindowKospi -gt 0) { $TrinitySafetyWindowKospi } else { $TrinitySafetyWindow })
    trinity_auto_safety_consecutive_threshold_kospi = $(if ($TrinitySafetyConsecutiveThresholdKospi -gt 0) { $TrinitySafetyConsecutiveThresholdKospi } else { $TrinitySafetyConsecutiveThreshold })
    trinity_auto_safety_window_btc = $(if ($TrinitySafetyWindowBtc -gt 0) { $TrinitySafetyWindowBtc } else { $TrinitySafetyWindow })
    trinity_auto_safety_consecutive_threshold_btc = $(if ($TrinitySafetyConsecutiveThresholdBtc -gt 0) { $TrinitySafetyConsecutiveThresholdBtc } else { $TrinitySafetyConsecutiveThreshold })
    trinity_btc_prediction_id  = $trinityBtcPredictionId
    trinity_btc_brier_score_3class = $trinityBtcBrier
    trinity_btc_regime_decision = $trinityBtcRegimeDecision
    trinity_btc_promotion_gate_path = $trinityBtcPromotionGateOut
    trinity_btc_promotion_recommendation_path = $trinityBtcPromotionRecommendationOut
    trinity_btc_promotion_execution_path = $trinityBtcPromotionExecutionOut
    risk_profile_sync_path     = $riskProfilePath
    runtime_health_guard_path  = $runtimeHealthOut
    runtime_health_status      = $runtimeHealthStatus
    runtime_health_should_pause_trading = $runtimeHealthShouldPauseTrading
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
if ($FailOnRuntimeHealthRed -and $runtimeHealthStatus -eq "red") {
    exit 3
}

$crossLensScript = Join-Path $WorkspaceRoot "scripts\build_cross_lens_rag_fusion_v1.py"
$sphereScript = Join-Path $WorkspaceRoot "scripts\assemble_three_lens_sphere_envelope_v1.py"
if ($IncludeCrossLensRagFusion -and -not $SkipCrossLensRagFusion) {
    if (Test-Path -LiteralPath $crossLensScript) {
        Write-Host "==> build_cross_lens_rag_fusion_v1.py (Track B; commander Telegram I-c)"
        & py scripts\build_cross_lens_rag_fusion_v1.py --skip-alert-emit
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "build_cross_lens_rag_fusion_v1.py exit $LASTEXITCODE; Telegram cross-lens block may be stale."
        }
    }
    else {
        Write-Warning "Missing: $crossLensScript"
    }
    if (Test-Path -LiteralPath $sphereScript) {
        Write-Host "==> assemble_three_lens_sphere_envelope_v1.py (4RAG pointers; Telegram I-d)"
        & py scripts\assemble_three_lens_sphere_envelope_v1.py
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "assemble_three_lens_sphere_envelope_v1.py exit $LASTEXITCODE; Telegram 4RAG block may be stale."
        }
    }
    else {
        Write-Warning "Missing: $sphereScript"
    }
}

Write-Host "==> build_prophecy_hit_rate_ssot_pointer_v1.py"
& py scripts\build_prophecy_hit_rate_ssot_pointer_v1.py
if ($LASTEXITCODE -ne 0) {
    throw "build_prophecy_hit_rate_ssot_pointer_v1.py exit $LASTEXITCODE"
}

$kospiBriefPs1 = Join-Path $WorkspaceRoot "scripts\Invoke-ProphecyDualLegAndKospiBrief_v1.ps1"
if ($IncludeKospiMorningBrief -and -not $SkipKospiMorningBrief) {
    if (Test-Path -LiteralPath $kospiBriefPs1) {
        Write-Host "==> Invoke-ProphecyDualLegAndKospiBrief_v1.ps1 (KOSPI morning onepager for 08:28 TG)"
        & powershell -NoProfile -ExecutionPolicy Bypass -File $kospiBriefPs1 -WorkspaceRoot $WorkspaceRoot
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Invoke-ProphecyDualLegAndKospiBrief_v1.ps1 exit $LASTEXITCODE; prophecy TG market block may be stale."
        }
    }
    else {
        Write-Warning "Missing: $kospiBriefPs1"
    }
}

Write-Host "OK: Daily prophecy eval finished. Operational: $evalOut Headline KPI (unchanged unless promoted): $headlineEvalOut Log: $logPath"
