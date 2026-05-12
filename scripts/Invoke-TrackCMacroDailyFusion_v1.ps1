<#
.SYNOPSIS
  Single daily entrypoint: Fragility+macro smoke (with weekly + webhooks) → forward log chain → Logos 4D X/Y → lens music M31 hormone trend (optional) → Track C ops dashboard.

.DESCRIPTION
  Avoids duplicate fragility runs: Invoke-FragilityMacroRiskDaily runs the full chain once; forward and logos chains use -SkipFragilityChain.

  Typical local test (no webhooks, no public exodus fetch):
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-TrackCMacroDailyFusion_v1.ps1 -SkipGateAlert -SkipExodusSourceFetch

  Optional: skip Role Router vs S1 shadow advisory append (non-gating):
    ... -SkipRoleRouterShadowAdvisory

  Optional meta-layer audit (after fusion steps): pass a JSON file or a markdown file containing a ```json envelope block.
    -File ... -MetaLayerEnvelopePath C:\path\envelope.json

.NOTES
  Scheduled task: Register-TrackCMacroDailyFusionTask.ps1 (use -UnregisterLegacyTasks when replacing
  MKM-Fragility-MacroRisk-Daily + MacroRiskForwardDailyChain). Re-register with the same -TaskName to
  change flags (e.g. -SkipExodusSourceFetch, -LensMusicPromotionGateSoftM31 for cold-start M31). Spot-check: Verify-TrackCMacroDailyFusionScheduledTask_v1.ps1.
#>
[CmdletBinding()]
param(
    [switch]$PreferFred,
    [string]$AssetScope = "BTC-USD",
    [ValidateSet("1h", "4h", "24h", "7d")]
    [string]$Horizon = "24h",

    [switch]$SkipGateAlert,
    [switch]$SkipFailureAlert,

    [switch]$SkipExodusSourceFetch,
    [switch]$SkipForwardChain,
    [switch]$SkipLogosChain,
    [switch]$SkipOpsDashboard,

    # Skip M31 hormone trend + WATCH-only webhook before ops dashboard (default: run when dashboard runs).
    [switch]$SkipLensMusicHormoneTrend,
    [switch]$SkipLensMusicPromotionGate,
    # Staging / cold-start: pass --allow-soft-m31 to promotion gate (see check_lens_music_symbolic_audio_promotion_gate_v1.py).
    [switch]$LensMusicPromotionGateSoftM31,
    [switch]$AllowCommercialUnlockInFusion,

    # Role-router multiscenario opt vs lens S1 shadow gate (append-only log; non-gating).
    [switch]$SkipRoleRouterShadowAdvisory,

    # Optional: run mkm_meta_layer_envelope_v1.py after fusion (JSON path or markdown with ```json envelope).
    [string]$MetaLayerEnvelopePath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

function Invoke-FusionStep {
    param(
        [string]$Name,
        [scriptblock]$Action
    )
    Write-Host "[trackc-macro-fusion] $Name"
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "Fusion step failed: $Name (exit=$LASTEXITCODE)"
    }
}

$fragilityDaily = Join-Path $PSScriptRoot "Invoke-FragilityMacroRiskDaily.ps1"
$forwardDaily = Join-Path $PSScriptRoot "run_macro_risk_forward_daily_chain_v1.ps1"
$logosChain = Join-Path $PSScriptRoot "run_logos_4d_state_chain_v1.ps1"
$logosRegimeResonanceShadow = Join-Path $PSScriptRoot "build_logos_regime_resonance_shadow_signal_v1.py"
$logosQuerySuite = Join-Path $PSScriptRoot "run_logos_semantic_query_smoke_suite_v1.py"
$logosShadowPromotion = Join-Path $PSScriptRoot "promote_logos_to_shadow_live_v1.py"
$logosShadowInsight = Join-Path $PSScriptRoot "build_logos_shadow_insight_report_v1.py"
$logosShadowDailyMetrics = Join-Path $PSScriptRoot "append_logos_shadow_daily_metrics_v1.py"
$logosShadowWeeklyGate = Join-Path $PSScriptRoot "build_logos_shadow_weekly_gate_v1.py"
$logosShadowWeeklyGateBootstrap = Join-Path $PSScriptRoot "build_logos_shadow_weekly_gate_v1.py"
$logosShadowWeeklyTrend = Join-Path $PSScriptRoot "build_logos_shadow_weekly_trend_report_v1.py"
$logosShadowAlertDecision = Join-Path $PSScriptRoot "build_logos_shadow_alert_decision_v1.py"
$logosShadowKpiProgress = Join-Path $PSScriptRoot "build_logos_shadow_promotion_kpi_progress_v1.py"
$logosResponsePolicyCheck = Join-Path $PSScriptRoot "build_logos_response_policy_check_v1.py"
$logosS1ShadowReviewPacket = Join-Path $PSScriptRoot "build_logos_s1_shadow_promotion_review_packet_v1.py"
$roleRouterS1ShadowAdvisory = Join-Path $PSScriptRoot "build_role_router_s1_shadow_advisory_v1.py"
$hormoneTrend = Join-Path $PSScriptRoot "build_lens_music_hormone_trend_v1.py"
$hormoneTrendWebhook = Join-Path $PSScriptRoot "dispatch_lens_music_hormone_trend_webhook_v1.py"
$lensMusicPromotionGate = Join-Path $PSScriptRoot "check_lens_music_symbolic_audio_promotion_gate_v1.py"
$lensMusicPromptPocThresholdSweep = Join-Path $PSScriptRoot "sweep_lens_music_prompt_poc_thresholds_v1.py"
$lensMusicPromptPocThresholdApply = Join-Path $PSScriptRoot "apply_lens_music_prompt_poc_threshold_recommendation_v1.py"
$lensMusicPromptPocThresholdDrift = Join-Path $PSScriptRoot "check_lens_music_prompt_poc_threshold_recommendation_drift_v1.py"
$lensMusicPromptPocThresholdDriftWebhook = Join-Path $PSScriptRoot "dispatch_lens_music_prompt_poc_threshold_drift_webhook_v1.py"
$lensMusicPromptPocThresholdPolicy = Join-Path $PSScriptRoot "build_lens_music_prompt_poc_threshold_policy_v1.py"
$opsDashboard = Join-Path $PSScriptRoot "build_mkm_trackc_ops_dashboard_v1.py"
$approvalTicketPreflight = Join-Path $PSScriptRoot "check_mkm_approval_ticket_preflight_v1.py"
$approvalTicketBump = Join-Path $PSScriptRoot "bump_mkm_approval_ticket_run_count_v1.py"

$required = @($fragilityDaily, $forwardDaily, $logosChain, $logosRegimeResonanceShadow, $logosQuerySuite, $logosShadowPromotion, $logosShadowInsight, $logosShadowDailyMetrics, $logosShadowWeeklyGate, $logosShadowWeeklyGateBootstrap, $logosShadowWeeklyTrend, $logosShadowAlertDecision, $logosShadowKpiProgress, $logosResponsePolicyCheck, $logosS1ShadowReviewPacket)
if (-not $SkipRoleRouterShadowAdvisory) {
    $required += $roleRouterS1ShadowAdvisory
}
if (-not $SkipOpsDashboard) {
    $required += $opsDashboard
    if (-not $SkipLensMusicHormoneTrend) {
        $required += $hormoneTrend
        $required += $hormoneTrendWebhook
        $required += $lensMusicPromptPocThresholdSweep
        $required += $lensMusicPromptPocThresholdApply
        $required += $lensMusicPromptPocThresholdDrift
        $required += $lensMusicPromptPocThresholdDriftWebhook
        $required += $lensMusicPromptPocThresholdPolicy
        if (-not $SkipLensMusicPromotionGate) {
            $required += $lensMusicPromotionGate
        }
        $required += $approvalTicketPreflight
        $required += $approvalTicketBump
    }
}
foreach ($p in $required) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "Required file not found: $p"
    }
}

# 1) Fragility + macro risk API smoke + weekly fragility report + optional gate/failure webhooks
$fragArgs = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", $fragilityDaily,
    "-AssetScope", $AssetScope,
    "-Horizon", $Horizon
)
if ($PreferFred) { $fragArgs += "-PreferFred" }
if ($SkipGateAlert) { $fragArgs += "-SkipGateAlert" }
if ($SkipFailureAlert) { $fragArgs += "-SkipFailureAlert" }

Invoke-FusionStep -Name "Invoke-FragilityMacroRiskDaily (full chain)" -Action {
    powershell @fragArgs
}

# 2) Forward-testing chain (reuse fragility artifacts)
if (-not $SkipForwardChain) {
    $fwdArgs = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", $forwardDaily,
        "-SkipFragilityChain",
        "-AssetScope", $AssetScope,
        "-Horizon", $Horizon
    )
    if ($PreferFred) { $fwdArgs += "-PreferFred" }
    Invoke-FusionStep -Name "run_macro_risk_forward_daily_chain_v1" -Action {
        powershell @fwdArgs
    }
}
else {
    Write-Host "[trackc-macro-fusion] skip forward daily chain (SkipForwardChain)"
}

# 3) Exodus source + pressure + logos 4D state (reuse fragility artifacts)
if (-not $SkipLogosChain) {
    $logosArgs = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", $logosChain,
        "-SkipFragilityChain",
        "-AssetScope", $AssetScope,
        "-Horizon", $Horizon
    )
    if ($PreferFred) { $logosArgs += "-PreferFred" }
    if ($SkipExodusSourceFetch) { $logosArgs += "-SkipExodusSourceFetch" }
    Invoke-FusionStep -Name "run_logos_4d_state_chain_v1" -Action {
        powershell @logosArgs
    }
}
else {
    Write-Host "[trackc-macro-fusion] skip logos 4d chain (SkipLogosChain)"
}

# 4) Logos semantic query suite (daily)
Invoke-FusionStep -Name "build_logos_regime_resonance_shadow_signal_v1.py" -Action {
    Set-Location -LiteralPath $repoRoot
    py $logosRegimeResonanceShadow
}
Invoke-FusionStep -Name "run_logos_semantic_query_smoke_suite_v1.py" -Action {
    Set-Location -LiteralPath $repoRoot
    py $logosQuerySuite --query-set-json "docs/final/artifacts/logos_semantic_query_set_v3.json"
}

# 5) Logos shadow promotion artifacts (daily non-gating)
Invoke-FusionStep -Name "promote_logos_to_shadow_live_v1.py" -Action {
    Set-Location -LiteralPath $repoRoot
    py $logosShadowPromotion --reason "TrackCMacroDailyFusion auto-run"
}

# 6) Shadow daily metrics append + weekly gate snapshot
Invoke-FusionStep -Name "append_logos_shadow_daily_metrics_v1.py" -Action {
    Set-Location -LiteralPath $repoRoot
    py $logosShadowDailyMetrics
}
Invoke-FusionStep -Name "build_logos_shadow_weekly_gate_v1.py" -Action {
    Set-Location -LiteralPath $repoRoot
    py $logosShadowWeeklyGate
}
Invoke-FusionStep -Name "build_logos_shadow_weekly_gate_v1.py (bootstrap)" -Action {
    Set-Location -LiteralPath $repoRoot
    py $logosShadowWeeklyGateBootstrap --profile bootstrap --output-json "docs/final/artifacts/logos_shadow_weekly_gate_bootstrap_latest.json"
}
Invoke-FusionStep -Name "build_logos_shadow_weekly_trend_report_v1.py" -Action {
    Set-Location -LiteralPath $repoRoot
    py $logosShadowWeeklyTrend
}
Invoke-FusionStep -Name "build_logos_shadow_alert_decision_v1.py" -Action {
    Set-Location -LiteralPath $repoRoot
    py $logosShadowAlertDecision
}
Invoke-FusionStep -Name "build_logos_shadow_promotion_kpi_progress_v1.py" -Action {
    Set-Location -LiteralPath $repoRoot
    py $logosShadowKpiProgress
}
Invoke-FusionStep -Name "build_logos_shadow_insight_report_v1.py (refresh weekly decision)" -Action {
    Set-Location -LiteralPath $repoRoot
    py $logosShadowInsight
}
Invoke-FusionStep -Name "build_logos_response_policy_check_v1.py" -Action {
    Set-Location -LiteralPath $repoRoot
    py $logosResponsePolicyCheck
}
Invoke-FusionStep -Name "build_logos_s1_shadow_promotion_review_packet_v1.py" -Action {
    Set-Location -LiteralPath $repoRoot
    py $logosS1ShadowReviewPacket
}

# 6b) Role router vs S1 shadow governance (advisory_only; append-only log)
if (-not $SkipRoleRouterShadowAdvisory) {
    Invoke-FusionStep -Name "build_role_router_s1_shadow_advisory_v1.py" -Action {
        Set-Location -LiteralPath $repoRoot
        py $roleRouterS1ShadowAdvisory
    }
}
else {
    Write-Host "[trackc-macro-fusion] skip role router S1 shadow advisory (SkipRoleRouterShadowAdvisory)"
}

# 7) Lens music M31 hormone trend + optional WATCH webhook (before ops dashboard reads those artifacts)
if (-not $SkipOpsDashboard) {
    $ticketReqFusion = $env:MKM_APPROVAL_TICKET_REQUIRED
    $ticketGateFusion = ($ticketReqFusion -eq "1" -or $ticketReqFusion -ieq "true")
    if (-not $SkipLensMusicHormoneTrend) {
        if ($ticketGateFusion) {
            Invoke-FusionStep -Name "check_mkm_approval_ticket_preflight_v1.py (trackc_macro_daily_fusion_lens_music_threshold)" -Action {
                Set-Location -LiteralPath $repoRoot
                py $approvalTicketPreflight --execution-tag trackc_macro_daily_fusion_lens_music_threshold
            }
        }
        Invoke-FusionStep -Name "build_lens_music_hormone_trend_v1.py" -Action {
            Set-Location -LiteralPath $repoRoot
            py $hormoneTrend
        }
        Invoke-FusionStep -Name "dispatch_lens_music_hormone_trend_webhook_v1.py" -Action {
            Set-Location -LiteralPath $repoRoot
            py $hormoneTrendWebhook
        }
        if (-not $SkipLensMusicPromotionGate) {
            $gateLabel = if ($LensMusicPromotionGateSoftM31) {
                "check_lens_music_symbolic_audio_promotion_gate_v1.py (m31-profile=soft)"
            } else {
                "check_lens_music_symbolic_audio_promotion_gate_v1.py (m31-profile=strict)"
            }
            Invoke-FusionStep -Name $gateLabel -Action {
                Set-Location -LiteralPath $repoRoot
                $gateArgs = @($lensMusicPromotionGate)
                if ($LensMusicPromotionGateSoftM31) {
                    $gateArgs += "--allow-soft-m31"
                }
                if ($AllowCommercialUnlockInFusion) {
                    $gateArgs += "--allow-commercial-unlock"
                }
                py @gateArgs
            }
        }
        else {
            Write-Host "[trackc-macro-fusion] skip lens music promotion gate (SkipLensMusicPromotionGate)"
        }
        Invoke-FusionStep -Name "build_lens_music_prompt_poc_threshold_policy_v1.py" -Action {
            Set-Location -LiteralPath $repoRoot
            py $lensMusicPromptPocThresholdSweep
            py $lensMusicPromptPocThresholdApply
            py $lensMusicPromptPocThresholdDrift
            py $lensMusicPromptPocThresholdDriftWebhook
            py $lensMusicPromptPocThresholdPolicy
        }
        if ($ticketGateFusion) {
            Invoke-FusionStep -Name "bump_mkm_approval_ticket_run_count_v1.py (lens-music fusion)" -Action {
                Set-Location -LiteralPath $repoRoot
                py $approvalTicketBump
            }
        }
    }
    else {
        Write-Host "[trackc-macro-fusion] skip lens music hormone trend + webhook (SkipLensMusicHormoneTrend)"
    }

    Invoke-FusionStep -Name "build_mkm_trackc_ops_dashboard_v1.py" -Action {
        Set-Location -LiteralPath $repoRoot
        py $opsDashboard
    }
}
else {
    Write-Host "[trackc-macro-fusion] skip ops dashboard (SkipOpsDashboard)"
}

if ([string]::IsNullOrWhiteSpace($MetaLayerEnvelopePath)) {
    Write-Host "[trackc-macro-fusion] skip meta-layer envelope (MetaLayerEnvelopePath empty)"
}
else {
    $metaPath = $MetaLayerEnvelopePath.Trim()
    if (-not (Test-Path -LiteralPath $metaPath)) {
        throw "MetaLayerEnvelopePath not found: $metaPath"
    }
    $pyGate = Join-Path $PSScriptRoot "mkm_meta_layer_envelope_v1.py"
    if (-not (Test-Path -LiteralPath $pyGate)) {
        throw "Required file not found: $pyGate"
    }
    Write-Host "[trackc-macro-fusion] meta-layer envelope gate: $metaPath"
    $mission = "trackc-macro-daily-fusion"
    $actor = "Invoke-TrackCMacroDailyFusion_v1"
    if ($metaPath.EndsWith(".json", [System.StringComparison]::OrdinalIgnoreCase)) {
        py $pyGate append --json-file $metaPath --repo-root $repoRoot --mission-id $mission --actor $actor
    }
    else {
        py $pyGate audit-markdown --markdown-file $metaPath --repo-root $repoRoot --mission-id $mission --actor $actor
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Meta-layer envelope gate failed (exit=$LASTEXITCODE)"
    }
}

Write-Host "[trackc-macro-fusion] PASS"
Write-Host "[trackc-macro-fusion] fragility_daily_json=$repoRoot/reports/fragility_macro_risk_daily_latest.json"
Write-Host "[trackc-macro-fusion] logos4d=$repoRoot/docs/final/artifacts/logos_4d_state_v1_latest.json"
Write-Host "[trackc-macro-fusion] logos_regime_resonance_shadow=$repoRoot/docs/final/artifacts/logos_regime_resonance_shadow_signal_latest.json"
Write-Host "[trackc-macro-fusion] logos_shadow_promotion=$repoRoot/docs/final/artifacts/logos_shadow_promotion_status_latest.json"
Write-Host "[trackc-macro-fusion] logos_shadow_insight=$repoRoot/docs/final/artifacts/logos_shadow_insight_latest.json"
Write-Host "[trackc-macro-fusion] logos_shadow_weekly_gate=$repoRoot/docs/final/artifacts/logos_shadow_weekly_gate_latest.json"
Write-Host "[trackc-macro-fusion] logos_shadow_weekly_gate_bootstrap=$repoRoot/docs/final/artifacts/logos_shadow_weekly_gate_bootstrap_latest.json"
Write-Host "[trackc-macro-fusion] logos_shadow_weekly_trend=$repoRoot/docs/final/artifacts/logos_shadow_weekly_trend_report_latest.json"
Write-Host "[trackc-macro-fusion] logos_shadow_alert_decision=$repoRoot/docs/final/artifacts/logos_shadow_alert_decision_latest.json"
Write-Host "[trackc-macro-fusion] logos_shadow_kpi_progress=$repoRoot/docs/final/artifacts/logos_shadow_promotion_kpi_progress_latest.json"
Write-Host "[trackc-macro-fusion] logos_response_policy_check=$repoRoot/docs/final/artifacts/logos_response_policy_check_latest.json"
Write-Host "[trackc-macro-fusion] logos_s1_shadow_promotion_review_packet=$repoRoot/docs/final/artifacts/logos_s1_shadow_promotion_review_packet_latest.json"
Write-Host "[trackc-macro-fusion] role_router_s1_shadow_advisory=$repoRoot/docs/final/artifacts/role_router_s1_shadow_advisory_latest.json"
Write-Host "[trackc-macro-fusion] lens_music_hormone_trend=$repoRoot/docs/final/artifacts/lens_music_hormone_trend_latest.json"
Write-Host "[trackc-macro-fusion] lens_music_hormone_trend_webhook_dispatch=$repoRoot/docs/final/artifacts/lens_music_hormone_trend_webhook_dispatch_latest.json"
Write-Host "[trackc-macro-fusion] ops_dashboard=$repoRoot/docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json"
