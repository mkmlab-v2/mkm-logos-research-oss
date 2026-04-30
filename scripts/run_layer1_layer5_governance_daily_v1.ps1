<#
.SYNOPSIS
  Run daily Layer1/Layer5 governance verification chain.

.DESCRIPTION
  Refreshes Layer5 benchmark, Layer1 router benchmark, integrated gate report,
  and governance readiness status in a single deterministic chain.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$SampleSize = 50,
    [int]$Seed = 42,
    [int]$MinApprovedSamples = 50,
    [switch]$UpdateBaselineLock
)

$ErrorActionPreference = "Stop"

$goldset = Join-Path $WorkspaceRoot "docs\final\artifacts\layer5_incident_goldset_human_v1_latest.jsonl"
$layer5Out = Join-Path $WorkspaceRoot "docs\final\artifacts\layer5_policy_gate_benchmark_latest.json"
$layer1Out = Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_router_benchmark_latest.json"
$integratedOut = Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_integrated_gate_report_latest.json"
$readinessOut = Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_governance_readiness_latest.json"
$goldsetSummary = Join-Path $WorkspaceRoot "docs\final\artifacts\layer5_incident_goldset_human_summary_latest.json"
$baselineLockOut = Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_baseline_lock_latest.json"
$baselineDriftOut = Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_baseline_drift_check_latest.json"
$alertOut = Join-Path $WorkspaceRoot "docs\final\artifacts\layer1_layer5_readiness_alert_latest.json"
$emotionMappingOut = Join-Path $WorkspaceRoot "docs\final\artifacts\emotion_state_mapping_latest.json"
$emotionShadowOut = Join-Path $WorkspaceRoot "docs\final\artifacts\emotion_state_shadow_eval_latest.json"
$emotionGateOut = Join-Path $WorkspaceRoot "docs\final\artifacts\emotion_state_promotion_gate_latest.json"
$emotionPromotedOut = Join-Path $WorkspaceRoot "docs\final\artifacts\emotion_state_track_a_promoted_latest.json"
$emotionPreflightOut = Join-Path $WorkspaceRoot "docs\final\artifacts\emotion_state_live_preflight_gate_latest.json"
$kmhSignalOut = Join-Path $WorkspaceRoot "docs\final\artifacts\emotion_state_kmh_runtime_signal_latest.json"
$profileOut = Join-Path $WorkspaceRoot "docs\final\artifacts\cursor_ai_operating_profile_v1_latest.json"

if (-not (Test-Path -LiteralPath $goldset)) {
    throw "Goldset not found: $goldset"
}

& py (Join-Path $WorkspaceRoot "scripts\benchmark_layer5_policy_gate_v1.py") `
    --input-jsonl $goldset `
    --sample-size $SampleSize `
    --seed $Seed `
    --output-json $layer5Out
if ($LASTEXITCODE -ne 0) { throw "Layer5 benchmark failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\benchmark_layer1_router_v1.py") `
    --input-jsonl $goldset `
    --output-json $layer1Out `
    --min-router-accuracy 0.95
if ($LASTEXITCODE -ne 0) { throw "Layer1 benchmark failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\build_layer1_layer5_integrated_gate_report_v1.py") `
    --layer1-json $layer1Out `
    --layer5-json $layer5Out `
    --output-json $integratedOut `
    --min-approved-samples $MinApprovedSamples
if ($LASTEXITCODE -ne 0) { throw "Integrated gate build failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\check_layer1_layer5_governance_readiness_v1.py") `
    --integrated-json $integratedOut `
    --goldset-summary-json $goldsetSummary `
    --output-json $readinessOut `
    --require-decision GO_CONTROLLED `
    --min-approved-count $MinApprovedSamples
if ($LASTEXITCODE -ne 0) { throw "Governance readiness check failed ($LASTEXITCODE)" }

if ($UpdateBaselineLock -or -not (Test-Path -LiteralPath $baselineLockOut)) {
    & py (Join-Path $WorkspaceRoot "scripts\build_layer1_layer5_baseline_lock_v1.py") `
        --layer1-json $layer1Out `
        --layer5-json $layer5Out `
        --integrated-json $integratedOut `
        --readiness-json $readinessOut `
        --goldset-summary-json $goldsetSummary `
        --output-json $baselineLockOut
    if ($LASTEXITCODE -ne 0) { throw "Baseline lock build failed ($LASTEXITCODE)" }
}

& py (Join-Path $WorkspaceRoot "scripts\send_layer1_layer5_readiness_alert_v1.py") `
    --readiness-json $readinessOut `
    --output-json $alertOut
if ($LASTEXITCODE -ne 0) { throw "Readiness alert dispatch step failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\check_layer1_layer5_baseline_drift_v1.py") `
    --baseline-lock-json $baselineLockOut `
    --layer1-json $layer1Out `
    --layer5-json $layer5Out `
    --integrated-json $integratedOut `
    --readiness-json $readinessOut `
    --goldset-summary-json $goldsetSummary `
    --output-json $baselineDriftOut
if ($LASTEXITCODE -ne 0) { throw "Baseline drift check step failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\build_emotion_state_kmh_runtime_signal_from_artifacts_v1.py") `
    --layer1-json $layer1Out `
    --layer5-json $layer5Out `
    --drift-json $baselineDriftOut `
    --output-json $kmhSignalOut
if ($LASTEXITCODE -ne 0) { throw "Emotion kmh runtime signal build failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\build_emotion_state_mapping_v1.py") `
    --output-json $emotionMappingOut
if ($LASTEXITCODE -ne 0) { throw "Emotion mapping build failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\run_emotion_state_shadow_eval_v1.py") `
    --mapping-json $emotionMappingOut `
    --layer1-json $layer1Out `
    --layer5-json $layer5Out `
    --output-json $emotionShadowOut
if ($LASTEXITCODE -ne 0) { throw "Emotion shadow eval failed ($LASTEXITCODE)" }

& py (Join-Path $WorkspaceRoot "scripts\check_emotion_state_promotion_gate_v1.py") `
    --eval-json $emotionShadowOut `
    --output-json $emotionGateOut `
    --min-stability-score 0.95 `
    --max-fpr 0.05 `
    --max-p95-ms 500
if ($LASTEXITCODE -ne 0) { throw "Emotion promotion gate failed ($LASTEXITCODE)" }

$emotionPromotedStatus = "MISSING"
if (Test-Path -LiteralPath $emotionPromotedOut) {
    $emotionPromoted = Get-Content -LiteralPath $emotionPromotedOut -Raw | ConvertFrom-Json
    $emotionPromotedStatus = [string]$emotionPromoted.status
}
if ($emotionPromotedStatus -ne "PROMOTED_TRACK_A_CANDIDATE") {
    throw "Emotion promoted status check failed: expected PROMOTED_TRACK_A_CANDIDATE, got '$emotionPromotedStatus'"
}

$zKm = 0.0
if (Test-Path -LiteralPath $kmhSignalOut) {
    $kmhSignal = Get-Content -LiteralPath $kmhSignalOut -Raw | ConvertFrom-Json
    if ($null -ne $kmhSignal.z_km) {
        $zKm = [double]$kmhSignal.z_km
    }
}

$alpha = 0.03
$tauMin = 0.03
$tauMax = 0.08
$maxLayer5Fpr = 0.05
$maxSignoffAgeHours = 168.0
if (Test-Path -LiteralPath $profileOut) {
    $profile = Get-Content -LiteralPath $profileOut -Raw | ConvertFrom-Json
    if ($null -ne $profile.emotion_control.alpha) { $alpha = [double]$profile.emotion_control.alpha }
    if ($null -ne $profile.emotion_control.tau_min) { $tauMin = [double]$profile.emotion_control.tau_min }
    if ($null -ne $profile.emotion_control.tau_max) { $tauMax = [double]$profile.emotion_control.tau_max }
    if ($null -ne $profile.gates.max_layer5_fpr) { $maxLayer5Fpr = [double]$profile.gates.max_layer5_fpr }
    if ($null -ne $profile.gates.max_signoff_age_hours) { $maxSignoffAgeHours = [double]$profile.gates.max_signoff_age_hours }
}

& py (Join-Path $WorkspaceRoot "scripts\check_emotion_state_live_preflight_gate_v1.py") `
    --human-signoff-json (Join-Path $WorkspaceRoot "docs\final\artifacts\emotion_state_release_human_signoff_latest.json") `
    --baseline-drift-json $baselineDriftOut `
    --layer5-json $layer5Out `
    --enable-kmh-dynamic `
    --z-km $zKm `
    --alpha $alpha `
    --tau-min $tauMin `
    --tau-max $tauMax `
    --max-layer5-fpr $maxLayer5Fpr `
    --max-signoff-age-hours $maxSignoffAgeHours `
    --output-json $emotionPreflightOut
if ($LASTEXITCODE -ne 0) { throw "Emotion live preflight failed ($LASTEXITCODE)" }

$preflightDecision = "UNKNOWN"
if (Test-Path -LiteralPath $emotionPreflightOut) {
    $preflight = Get-Content -LiteralPath $emotionPreflightOut -Raw | ConvertFrom-Json
    $preflightDecision = [string]$preflight.decision
}
if ($preflightDecision -ne "GO_LIVE_CANDIDATE") {
    throw "Emotion preflight decision failed: expected GO_LIVE_CANDIDATE, got '$preflightDecision'"
}

Write-Host "DONE: Layer1/Layer5 daily governance chain."
Write-Host "Readiness artifact: $readinessOut"
Write-Host "Emotion promotion artifact: $emotionGateOut"
Write-Host "Emotion promoted artifact: $emotionPromotedOut"
Write-Host "Emotion preflight artifact: $emotionPreflightOut"
