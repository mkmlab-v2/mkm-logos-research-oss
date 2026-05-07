param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$IncludeDualLegDashboardChain,
    [int]$DualLegRecentTradingDays = 30
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

# BL-009: regenerate external briefing markdown (EN/KO) from latest Fact-Lock artifacts.
$externalBriefingGenerator = Join-Path $WorkspaceRoot "scripts\build_official_external_briefing_v1.py"
if (Test-Path -LiteralPath $externalBriefingGenerator) {
    & py $externalBriefingGenerator
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = $LASTEXITCODE
    }
}

if ($exitCode -ne 0) {
    exit $exitCode
}

exit 0
