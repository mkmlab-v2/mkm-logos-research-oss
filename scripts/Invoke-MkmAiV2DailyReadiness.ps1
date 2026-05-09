param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$IncludeDualLegDashboardChain,
    [int]$DualLegRecentTradingDays = 30,
    [switch]$EnableFallbackPostCutoffCriticalFail,
    [double]$FallbackPostCutoffWarnRate = 0.15,
    [switch]$IncludeLgHSPersuasionBridge,
    [ValidateSet("general", "performance", "safety", "schedule")]
    [string]$LgHSPersuasionQuestionType = "general"
)

$ErrorActionPreference = "Stop"

$cursorrulesEnforcer = Join-Path $WorkspaceRoot "scripts\enforce_cursorrules_slim_ssot.py"
if (Test-Path -LiteralPath $cursorrulesEnforcer) {
    & py $cursorrulesEnforcer --workspace-root $WorkspaceRoot
}

$runner = Join-Path $WorkspaceRoot "scripts\run_mkm_ai_v2_readiness_check.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

& powershell -NoProfile -ExecutionPolicy Bypass -File $runner -WorkspaceRoot $WorkspaceRoot
$exitCode = $LASTEXITCODE

$artifactPath = Join-Path $WorkspaceRoot "docs\final\artifacts\mkm_ai_v2_readiness_latest.json"
$overallPassed = $false
if (Test-Path -LiteralPath $artifactPath) {
    try {
        $artifact = Get-Content -LiteralPath $artifactPath -Raw | ConvertFrom-Json
        if ($artifact.overall_passed -eq $true) {
            $overallPassed = $true
        }
    }
    catch {
        $overallPassed = $false
    }
}

$reportDir = Join-Path $WorkspaceRoot "reports"
if (-not (Test-Path -LiteralPath $reportDir)) {
    New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
}

$logPath = Join-Path $reportDir "mkm_ai_v2_readiness_log.jsonl"
$row = [ordered]@{
    schema          = "mkm_ai_v2_readiness_daily_log_v1"
    ts_utc          = (Get-Date).ToUniversalTime().ToString("o")
    workspace_root  = $WorkspaceRoot
    exit_code       = $exitCode
    overall_passed  = $overallPassed
    artifact_path   = $artifactPath
}
($row | ConvertTo-Json -Compress) | Add-Content -LiteralPath $logPath -Encoding UTF8

function Test-DecisionLoggedToday {
    param(
        [string]$DecisionsLogPath,
        [string]$MissionId,
        [string]$Stage,
        [string]$Decision,
        [string]$Actor
    )
    if (-not (Test-Path -LiteralPath $DecisionsLogPath)) {
        return $false
    }
    $todayUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
    try {
        $lines = Get-Content -LiteralPath $DecisionsLogPath -Encoding UTF8
        foreach ($line in $lines) {
            if ([string]::IsNullOrWhiteSpace($line)) { continue }
            $obj = $line | ConvertFrom-Json -ErrorAction SilentlyContinue
            if ($null -eq $obj) { continue }
            $ts = [string]$obj.timestamp
            if ([string]::IsNullOrWhiteSpace($ts)) { continue }
            if (-not $ts.StartsWith($todayUtc)) { continue }
            if (($obj.mission_id -eq $MissionId) -and ($obj.stage -eq $Stage) -and ($obj.decision -eq $Decision) -and ($obj.actor -eq $Actor)) {
                return $true
            }
        }
    }
    catch {
        return $false
    }
    return $false
}

# Refresh rolling 7-day readiness summary artifact.
$weeklyBuilder = Join-Path $WorkspaceRoot "scripts\build_mkm_ai_v2_weekly_readiness_report.py"
if (Test-Path -LiteralPath $weeklyBuilder) {
    & py $weeklyBuilder --workspace-root $WorkspaceRoot --window-days 7
}

# Refresh promotion go/hold decision from latest readiness + weekly stats.
$promotionDecision = Join-Path $WorkspaceRoot "scripts\check_mkm_ai_v2_promotion_decision.py"
if (Test-Path -LiteralPath $promotionDecision) {
    & py $promotionDecision --workspace-root $WorkspaceRoot --min-pass-rate 95 --min-sample-count 3
}

# Sync lock artifact from latest promotion decision (auto downgrade/upgrade).
$promotionLockSync = Join-Path $WorkspaceRoot "scripts\sync_mkm_ai_v2_promotion_lock.py"
if (Test-Path -LiteralPath $promotionLockSync) {
    & py $promotionLockSync --workspace-root $WorkspaceRoot
}

# Refresh single status pointer for downstream consumers.
$statusPointer = Join-Path $WorkspaceRoot "scripts\build_mkm_ai_status_pointer.py"
if (Test-Path -LiteralPath $statusPointer) {
    & py $statusPointer --workspace-root $WorkspaceRoot
}

# Refresh human-readable status brief (markdown).
$statusBrief = Join-Path $WorkspaceRoot "scripts\build_mkm_ai_status_brief.py"
if (Test-Path -LiteralPath $statusBrief) {
    & py $statusBrief --workspace-root $WorkspaceRoot
}

# Refresh consolidated final ops bundle for one-file operational view.
$opsBundle = Join-Path $WorkspaceRoot "scripts\build_mkm_ai_final_ops_bundle.py"
if (Test-Path -LiteralPath $opsBundle) {
    & py $opsBundle --workspace-root $WorkspaceRoot
}

# Refresh Track C commercial delivery artifacts.
$trackCCommercialPackage = Join-Path $WorkspaceRoot "scripts\build_mkm_trackc_commercial_package.py"
if (Test-Path -LiteralPath $trackCCommercialPackage) {
    & py $trackCCommercialPackage
}

$trackCExternalOnepager = Join-Path $WorkspaceRoot "scripts\build_mkm_trackc_external_onepager_v1.py"
if (Test-Path -LiteralPath $trackCExternalOnepager) {
    & py $trackCExternalOnepager
}

$trackCApiSpecPackage = Join-Path $WorkspaceRoot "scripts\build_mkm_trackc_api_spec_package_v1.py"
if (Test-Path -LiteralPath $trackCApiSpecPackage) {
    & py $trackCApiSpecPackage
}

$trackCClientHandoff = Join-Path $WorkspaceRoot "scripts\build_mkm_trackc_client_handoff_package_v1.py"
if (Test-Path -LiteralPath $trackCClientHandoff) {
    & py $trackCClientHandoff
}

$paddleStatus = Join-Path $WorkspaceRoot "scripts\build_paddle_onboarding_status_v1.py"
if (Test-Path -LiteralPath $paddleStatus) {
    & py $paddleStatus --workspace-root $WorkspaceRoot
}

# Optional: refresh LG HS persuasion bridge artifact from latest emotion-reasoning state.
$lgHSPersuasionBridge = Join-Path $WorkspaceRoot "scripts\build_lg_hs_persuasion_bridge_v1.py"
if ($IncludeLgHSPersuasionBridge -and (Test-Path -LiteralPath $lgHSPersuasionBridge)) {
    & py $lgHSPersuasionBridge --question-type $LgHSPersuasionQuestionType
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
}

# Optional: one-click dual-leg (KOSPI/BTC) -> Track C dashboard chain.
$dualLegChainRan = $false
$dualLegChain = Join-Path $WorkspaceRoot "scripts\Run-TrackCDualLegDashboardChain.ps1"
if ($IncludeDualLegDashboardChain -and (Test-Path -LiteralPath $dualLegChain)) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $dualLegChain -WorkspaceRoot $WorkspaceRoot -RecentTradingDays $DualLegRecentTradingDays
    if ($LASTEXITCODE -eq 0) {
        $dualLegChainRan = $true
    } elseif ($exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
}

# Refresh one-file Track C operations dashboard.
$trackCOpsDashboard = Join-Path $WorkspaceRoot "scripts\build_mkm_trackc_ops_dashboard_v1.py"
if (-not $dualLegChainRan -and (Test-Path -LiteralPath $trackCOpsDashboard)) {
    & py $trackCOpsDashboard
}

$trackCOpsDashboardExec = Join-Path $WorkspaceRoot "scripts\build_mkm_trackc_ops_dashboard_exec_v1.py"
if (-not $dualLegChainRan -and (Test-Path -LiteralPath $trackCOpsDashboardExec)) {
    & py $trackCOpsDashboardExec
}

# Refresh Track C morning briefing artifact set (json + ko/en markdown).
$trackCMorningBriefing = Join-Path $WorkspaceRoot "scripts\build_trackc_macro_risk_morning_briefing_v1.py"
if (Test-Path -LiteralPath $trackCMorningBriefing) {
    & py $trackCMorningBriefing
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
    $briefingJson = Join-Path $WorkspaceRoot "docs\final\artifacts\trackc_macro_risk_morning_briefing_latest.json"
    if (Test-Path -LiteralPath $briefingJson) {
        try {
            $briefObj = Get-Content -LiteralPath $briefingJson -Raw -Encoding UTF8 | ConvertFrom-Json
            $shadowSection = $briefObj.shadow_pnl
            $shadowStatus = $null
            if ($null -ne $shadowSection) {
                $shadowStatus = [string]$shadowSection.shadow_pnl_status
            }
            if ([string]::IsNullOrWhiteSpace($shadowStatus)) {
                throw "missing shadow_pnl.shadow_pnl_status"
            }
            Write-Host "Shadow PnL briefing section check: PASS ($shadowStatus)"
        }
        catch {
            Write-Host "Shadow PnL briefing section check: FAIL ($($_.Exception.Message))" -ForegroundColor Yellow
            if ($exitCode -eq 0) { $exitCode = 1 }
        }
    }
    else {
        Write-Host "Shadow PnL briefing section check: FAIL (missing briefing json)" -ForegroundColor Yellow
        if ($exitCode -eq 0) { $exitCode = 1 }
    }
}

# Dispatch compliance-safe Track C B2B brief webhook payload (if webhook env is configured).
$trackCB2BDispatch = Join-Path $WorkspaceRoot "scripts\dispatch_trackc_b2b_brief_webhook_v1.py"
if (Test-Path -LiteralPath $trackCB2BDispatch) {
    & py $trackCB2BDispatch
}

# External channel guard: ensure onepager does not leak Shadow PnL fields.
$externalOnepagerJson = Join-Path $WorkspaceRoot "docs\final\artifacts\mkm_trackc_external_onepager_latest.json"
if (Test-Path -LiteralPath $externalOnepagerJson) {
    try {
        $onepagerObj = Get-Content -LiteralPath $externalOnepagerJson -Raw -Encoding UTF8 | ConvertFrom-Json
        $onepagerRaw = Get-Content -LiteralPath $externalOnepagerJson -Raw -Encoding UTF8
        $rawLower = $onepagerRaw.ToLowerInvariant()
        if ($rawLower.Contains("shadow_pnl") -and -not $rawLower.Contains('"shadow_pnl_disclosure": "disabled"')) {
            throw "external onepager contains unexpected shadow_pnl field"
        }
        Write-Host "External onepager shadow leakage check: PASS"
    }
    catch {
        Write-Host "External onepager shadow leakage check: FAIL ($($_.Exception.Message))" -ForegroundColor Yellow
        if ($exitCode -eq 0) { $exitCode = 1 }
    }
}

# Hard guard: fail daily runner if Track C handoff package degrades.
$trackCGuard = Join-Path $WorkspaceRoot "scripts\check_mkm_trackc_client_handoff_guard.py"
if (Test-Path -LiteralPath $trackCGuard) {
    & py $trackCGuard --workspace-root $WorkspaceRoot
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
}

# BL-004 hard gate: fail when A-track decision inputs are contaminated by B-track paths.
$abContaminationGate = Join-Path $WorkspaceRoot "scripts\check_mkm_atrack_btrack_contamination_gate_v1.py"
if (Test-Path -LiteralPath $abContaminationGate) {
    & py $abContaminationGate --a-track-json (Join-Path $WorkspaceRoot "docs\final\artifacts\a_track_go_nogo_status_latest.json") --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\mkm_atrack_btrack_contamination_gate_latest.json")
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
}

# BL-005 monitor: append WATCH streak log and refresh prolonged alert artifact.
$watchProlongedAlert = Join-Path $WorkspaceRoot "scripts\alert_mkm_trackc_watch_prolonged_v1.py"
if (Test-Path -LiteralPath $watchProlongedAlert) {
    & py $watchProlongedAlert --dashboard-json (Join-Path $WorkspaceRoot "docs\final\artifacts\mkm_trackc_ops_dashboard_latest.json") --kpi-contract-json (Join-Path $WorkspaceRoot "docs\final\artifacts\mkm_trackc_watch_exit_kpi_contract_latest.json") --state-log-jsonl (Join-Path $WorkspaceRoot "reports\mkm_trackc_watch_state_log.jsonl") --output-json (Join-Path $WorkspaceRoot "docs\final\artifacts\mkm_trackc_watch_prolonged_alert_latest.json")
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
}

# BL-006: build model-mix cost/latency tracking artifact.
$modelMixCostLatency = Join-Path $WorkspaceRoot "scripts\build_mkm_model_mix_cost_latency_report_v1.py"
if (Test-Path -LiteralPath $modelMixCostLatency) {
    & py $modelMixCostLatency --workspace-root $WorkspaceRoot
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
}

# BL-007: append unified decision ledger row.
$decisionLedger = Join-Path $WorkspaceRoot "scripts\append_mkm_decision_ledger_v1.py"
if (Test-Path -LiteralPath $decisionLedger) {
    & py $decisionLedger --workspace-root $WorkspaceRoot --actor "daily-readiness-runner" --decision "GO_WITH_CONSERVATIVE_GUARD" --reason "Automated daily snapshot with WATCH guard policy."
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
}

# BL-008: regenerate filled fact-lock templates from latest artifacts.
$filledTemplates = Join-Path $WorkspaceRoot "scripts\build_mkm_fact_lock_templates_filled_v1.py"
if (Test-Path -LiteralPath $filledTemplates) {
    & py $filledTemplates --workspace-root $WorkspaceRoot
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
}

# BL-008.5: regenerate 30y long-horizon claim guard artifact.
$thirtyYearGuard = Join-Path $WorkspaceRoot "scripts\build_prophecy_lens_combo_backtest_30y_latest.py"
if (Test-Path -LiteralPath $thirtyYearGuard) {
    & py $thirtyYearGuard
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
}

# BL-008.55: refresh Sasang holdout eval with full cohort defaults.
$sasangHoldoutRefresh = Join-Path $WorkspaceRoot "scripts\run_agct_sasang_holdout_eval_refresh_v1.py"
if (Test-Path -LiteralPath $sasangHoldoutRefresh) {
    & py $sasangHoldoutRefresh
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
}

# BL-008.6: refresh Sasang promotion blocker snapshot.
$sasangBlockers = Join-Path $WorkspaceRoot "scripts\check_sasang_promotion_blockers_v1.py"
if (Test-Path -LiteralPath $sasangBlockers) {
    & py $sasangBlockers --allow-alt-long-horizon-waiver --alt-min-available-years 4.99
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
}

# BL-008.7: rebuild threshold recalibration report for Sasang B-track stability.
$sasangThresholdRecal = Join-Path $WorkspaceRoot "scripts\build_sasang_btrack_threshold_recalibration_v1.py"
if (Test-Path -LiteralPath $sasangThresholdRecal) {
    & py $sasangThresholdRecal
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
}

# BL-009: regenerate external briefing markdown (EN/KO) from latest Fact-Lock artifacts.
$externalBriefingGenerator = Join-Path $WorkspaceRoot "scripts\build_official_external_briefing_v1.py"
if (Test-Path -LiteralPath $externalBriefingGenerator) {
    & py $externalBriefingGenerator
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
}

# BL-010: enforce Sasang dual-mode response formatting policy outputs.
$sasangRuleResponseBuilder = Join-Path $WorkspaceRoot "scripts\build_sasang_rule_based_response_v1.py"
if (Test-Path -LiteralPath $sasangRuleResponseBuilder) {
    & py $sasangRuleResponseBuilder --response-mode prod
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
}

# BL-011: refresh compression API fallback trigger telemetry (24h window summary).
$fallbackSummary = Join-Path $WorkspaceRoot "scripts\build_fallback_trigger_daily_summary_v1.py"
if (Test-Path -LiteralPath $fallbackSummary) {
    $fallbackProfile = Join-Path $WorkspaceRoot "docs\final\artifacts\fallback_trigger_threshold_profile_latest.json"
    $prevCutoff = $env:FALLBACK_TRIGGER_CUTOFF_UTC
    $cutoffApplied = $false
    if (Test-Path -LiteralPath $fallbackProfile) {
        try {
            $fp = Get-Content -LiteralPath $fallbackProfile -Raw -Encoding UTF8 | ConvertFrom-Json
            $cutoffRaw = [string]$fp.generated_at_utc
            if (-not [string]::IsNullOrWhiteSpace($cutoffRaw)) {
                $env:FALLBACK_TRIGGER_CUTOFF_UTC = $cutoffRaw
                $cutoffApplied = $true
            }
        }
        catch {
            Write-Host "WARN: fallback profile parse failed for cutoff propagation ($($_.Exception.Message))" -ForegroundColor Yellow
        }
    }

    & py $fallbackSummary
    if ($cutoffApplied) {
        if ([string]::IsNullOrWhiteSpace($prevCutoff)) {
            Remove-Item Env:FALLBACK_TRIGGER_CUTOFF_UTC -ErrorAction SilentlyContinue
        }
        else {
            $env:FALLBACK_TRIGGER_CUTOFF_UTC = $prevCutoff
        }
    }
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
    $fbJson = Join-Path $WorkspaceRoot "docs\final\artifacts\fallback_trigger_daily_summary_latest.json"
    if (Test-Path -LiteralPath $fbJson) {
        try {
            $fb = Get-Content -LiteralPath $fbJson -Raw -Encoding UTF8 | ConvertFrom-Json
            $rate = [double]$fb.fallback_trigger_rate
            $postWarnThresholdRaw = $env:FALLBACK_POST_CUTOFF_WARN_RATE
            $postWarnThreshold = $FallbackPostCutoffWarnRate
            if (-not [string]::IsNullOrWhiteSpace($postWarnThresholdRaw)) {
                try {
                    $postWarnThreshold = [double]$postWarnThresholdRaw
                }
                catch {
                    Write-Host "WARN: invalid FALLBACK_POST_CUTOFF_WARN_RATE=$postWarnThresholdRaw (using $FallbackPostCutoffWarnRate)" -ForegroundColor Yellow
                    $postWarnThreshold = $FallbackPostCutoffWarnRate
                }
            }
            if ($rate -gt 0.50) {
                Write-Host "WARN: fallback_trigger_rate high ($rate) — review thresholds or traffic mix." -ForegroundColor Yellow
            }
            else {
                Write-Host "Fallback telemetry summary: OK (fallback_trigger_rate=$rate)"
            }
            $pcs = $fb.post_cutoff_summary
            if ($null -ne $pcs) {
                $postRate = [double]$pcs.fallback_trigger_rate
                if ($postRate -gt $postWarnThreshold) {
                    Write-Host "WARN: post_cutoff fallback_trigger_rate high ($postRate > $postWarnThreshold) — recalibration may be needed." -ForegroundColor Yellow
                    $decisionLogger = Join-Path $WorkspaceRoot "scripts\log_agent_decision.py"
                    $decisionsLog = Join-Path $WorkspaceRoot "reports\agent_decisions_log.jsonl"
                    if ((Test-Path -LiteralPath $decisionLogger) -and -not (Test-DecisionLoggedToday -DecisionsLogPath $decisionsLog -MissionId "fallback_post_cutoff_watch_v1" -Stage "fallback_post_cutoff_watch" -Decision "WARN_POST_CUTOFF_RATE_HIGH" -Actor "daily-readiness-runner")) {
                        & py $decisionLogger --repo-root $WorkspaceRoot --mission-id "fallback_post_cutoff_watch_v1" --stage "fallback_post_cutoff_watch" --decision "WARN_POST_CUTOFF_RATE_HIGH" --evidence-path (Join-Path $WorkspaceRoot "docs\final\artifacts\fallback_trigger_daily_summary_latest.json") --actor "daily-readiness-runner" --risk-level "medium" --note ("post_cutoff_rate={0};threshold={1}" -f $postRate, $postWarnThreshold) | Out-Null
                    }
                }
                else {
                    Write-Host "Post-cutoff telemetry summary: OK (fallback_trigger_rate=$postRate, threshold=$postWarnThreshold)"
                }
            }
        }
        catch {
            Write-Host "WARN: fallback summary parse check failed ($($_.Exception.Message))" -ForegroundColor Yellow
            if ($exitCode -eq 0) { $exitCode = 1 }
        }

        $fallbackWatchReport = Join-Path $WorkspaceRoot "scripts\build_fallback_post_cutoff_watch_report_v1.py"
        if (Test-Path -LiteralPath $fallbackWatchReport) {
            $fallbackProfile = Join-Path $WorkspaceRoot "docs\final\artifacts\fallback_trigger_threshold_profile_latest.json"
            $prevBaselineReset = $env:FALLBACK_POST_CUTOFF_BASELINE_RESET_UTC
            $baselineResetApplied = $false
            if (Test-Path -LiteralPath $fallbackProfile) {
                try {
                    $fpWatch = Get-Content -LiteralPath $fallbackProfile -Raw -Encoding UTF8 | ConvertFrom-Json
                    $baselineRaw = [string]$fpWatch.generated_at_utc
                    if (-not [string]::IsNullOrWhiteSpace($baselineRaw)) {
                        $env:FALLBACK_POST_CUTOFF_BASELINE_RESET_UTC = $baselineRaw
                        $baselineResetApplied = $true
                    }
                }
                catch {
                    Write-Host "WARN: fallback profile parse failed for baseline reset propagation ($($_.Exception.Message))" -ForegroundColor Yellow
                }
            }
            & py $fallbackWatchReport | Out-Null
            if ($baselineResetApplied) {
                if ([string]::IsNullOrWhiteSpace($prevBaselineReset)) {
                    Remove-Item Env:FALLBACK_POST_CUTOFF_BASELINE_RESET_UTC -ErrorAction SilentlyContinue
                }
                else {
                    $env:FALLBACK_POST_CUTOFF_BASELINE_RESET_UTC = $prevBaselineReset
                }
            }
            $watchJson = Join-Path $WorkspaceRoot "docs\final\artifacts\fallback_post_cutoff_watch_report_latest.json"
            if (Test-Path -LiteralPath $watchJson) {
                try {
                    $watch = Get-Content -LiteralPath $watchJson -Raw -Encoding UTF8 | ConvertFrom-Json
                    $signal = [string](($watch.summary).signal)
                    if ($signal -eq "CRITICAL") {
                        Write-Host "WARN: fallback post-cutoff watch signal is CRITICAL - escalation recommended." -ForegroundColor Yellow
                        $decisionLogger = Join-Path $WorkspaceRoot "scripts\log_agent_decision.py"
                        $decisionsLog = Join-Path $WorkspaceRoot "reports\agent_decisions_log.jsonl"
                        if ((Test-Path -LiteralPath $decisionLogger) -and -not (Test-DecisionLoggedToday -DecisionsLogPath $decisionsLog -MissionId "fallback_post_cutoff_watch_v1" -Stage "fallback_post_cutoff_escalation" -Decision "CRITICAL_SIGNAL_ESCALATION" -Actor "daily-readiness-runner")) {
                            & py $decisionLogger --repo-root $WorkspaceRoot --mission-id "fallback_post_cutoff_watch_v1" --stage "fallback_post_cutoff_escalation" --decision "CRITICAL_SIGNAL_ESCALATION" --evidence-path $watchJson --actor "daily-readiness-runner" --risk-level "high" --note "signal=CRITICAL from fallback post-cutoff watch report" | Out-Null
                        }
                        $criticalFailRaw = [string]$env:FALLBACK_POST_CUTOFF_CRITICAL_FAIL
                        if (($EnableFallbackPostCutoffCriticalFail -or $criticalFailRaw -match '^(1|true|yes)$') -and $exitCode -eq 0) {
                            $exitCode = 2
                        }
                    }
                }
                catch {
                    Write-Host "WARN: fallback post-cutoff watch parse failed ($($_.Exception.Message))" -ForegroundColor Yellow
                }
            }

            $fallbackDiagnosis = Join-Path $WorkspaceRoot "scripts\build_fallback_post_cutoff_diagnosis_v1.py"
            if (Test-Path -LiteralPath $fallbackDiagnosis) {
                & py $fallbackDiagnosis | Out-Null
            }

            $fallbackObservationStatus = Join-Path $WorkspaceRoot "scripts\build_fallback_post_cutoff_observation_status_v1.py"
            if (Test-Path -LiteralPath $fallbackObservationStatus) {
                & py $fallbackObservationStatus | Out-Null
                $obsJson = Join-Path $WorkspaceRoot "docs\final\artifacts\fallback_post_cutoff_observation_status_latest.json"
                if (Test-Path -LiteralPath $obsJson) {
                    try {
                        $obs = Get-Content -LiteralPath $obsJson -Raw -Encoding UTF8 | ConvertFrom-Json
                        $obsDecision = [string]$obs.decision
                        if ($obsDecision -eq "GO_OBSERVATION_COMPLETE") {
                            Write-Host "Fallback post-cutoff observation status: GO (observation complete)"
                        }
                        elseif ($obsDecision -eq "HOLD_OBSERVATION_CONTINUE") {
                            Write-Host "WARN: fallback post-cutoff observation status is HOLD (observation continue)." -ForegroundColor Yellow
                        }
                    }
                    catch {
                        Write-Host "WARN: fallback post-cutoff observation status parse failed ($($_.Exception.Message))" -ForegroundColor Yellow
                    }
                }
            }
        }
    }
    else {
        Write-Host "WARN: missing fallback_trigger_daily_summary_latest.json after builder" -ForegroundColor Yellow
        if ($exitCode -eq 0) { $exitCode = 1 }
    }
}

# BL-012: refresh news-grade-plus scorecard and freeze timestamped snapshot.
$newsScorecardBuilder = Join-Path $WorkspaceRoot "scripts\build_news_grade_plus_scorecard_v1.py"
if (Test-Path -LiteralPath $newsScorecardBuilder) {
    & py $newsScorecardBuilder | Out-Null
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
    $newsScorecardJson = Join-Path $WorkspaceRoot "docs\final\artifacts\news_grade_plus_scorecard_latest.json"
    $newsScorecardMd = Join-Path $WorkspaceRoot "docs\final\artifacts\news_grade_plus_scorecard_latest.md"
    if ((Test-Path -LiteralPath $newsScorecardJson) -and (Test-Path -LiteralPath $newsScorecardMd)) {
        try {
            $stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
            $archiveDir = Join-Path $WorkspaceRoot "docs\final\artifacts\archive\news_grade_plus"
            if (-not (Test-Path -LiteralPath $archiveDir)) {
                New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null
            }
            $snapJson = Join-Path $archiveDir ("news_grade_plus_scorecard_{0}.json" -f $stamp)
            $snapMd = Join-Path $archiveDir ("news_grade_plus_scorecard_{0}.md" -f $stamp)
            Copy-Item -LiteralPath $newsScorecardJson -Destination $snapJson -Force
            Copy-Item -LiteralPath $newsScorecardMd -Destination $snapMd -Force
            Write-Host ("News grade plus snapshot: {0}" -f $snapJson)
        }
        catch {
            Write-Host "WARN: news grade plus snapshot freeze failed ($($_.Exception.Message))" -ForegroundColor Yellow
            if ($exitCode -eq 0) { $exitCode = 1 }
        }
    }
}

if ($exitCode -ne 0) {
    exit $exitCode
}

exit 0
