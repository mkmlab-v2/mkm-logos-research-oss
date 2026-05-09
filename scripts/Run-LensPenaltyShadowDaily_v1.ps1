<#
.SYNOPSIS
  Run daily lens penalty scoring in shadow mode (size-only recommendation).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$InputJson = "",
    [string]$EventsJsonl = "",
    [string]$StateJson = "",
    [string]$PolicyJson = "",
    [string]$OutJson = "",
    [string]$WeeklyOutJson = "",
    [int]$WeeklyWindowDays = 7
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

if ([string]::IsNullOrWhiteSpace($EventsJsonl)) {
    $EventsJsonl = "reports\daily_execution_insight_falsification_log.jsonl"
}
if ([string]::IsNullOrWhiteSpace($InputJson)) {
    $InputJson = "reports\daily_execution_falsification_input_latest.json"
}
if ([string]::IsNullOrWhiteSpace($StateJson)) {
    $StateJson = "docs\final\artifacts\lens_penalty_shadow_state_latest.json"
}
if ([string]::IsNullOrWhiteSpace($PolicyJson)) {
    $PolicyJson = "docs\final\artifacts\lens_penalty_policy_v1.json"
}
if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = "docs\final\artifacts\lens_penalty_daily_latest.json"
}
if ([string]::IsNullOrWhiteSpace($WeeklyOutJson)) {
    $WeeklyOutJson = "docs\final\artifacts\lens_penalty_shadow_weekly_report_latest.json"
}
$ApplyPolicyJson = "docs\final\artifacts\lens_penalty_apply_mode_policy_v1.json"
$autoApplyEnabled = $false
$stateBackupPath = ""
if (Test-Path -LiteralPath $ApplyPolicyJson) {
    try {
        $applyPolicy = Get-Content -LiteralPath $ApplyPolicyJson -Raw | ConvertFrom-Json
        $autoApplyEnabled = [bool]$applyPolicy.auto_apply_enabled
    } catch {
        $autoApplyEnabled = $false
    }
}

& py "scripts\build_daily_execution_falsification_input_v1.py" `
    --out $InputJson

& py "scripts\build_daily_execution_falsification_events_v1.py" `
    --input-json $InputJson `
    --events-jsonl $EventsJsonl `
    --out "docs\final\artifacts\daily_execution_falsification_events_latest.json"

& py "scripts\ensure_lens_penalty_shadow_state_v1.py" `
    --state-json $StateJson
$ensureStateExit = $LASTEXITCODE
if ($ensureStateExit -ne 0) { exit $ensureStateExit }

if ($autoApplyEnabled -and (Test-Path -LiteralPath $StateJson)) {
    $stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
    $stateBackupPath = "docs\final\artifacts\lens_penalty_shadow_state_backup_$stamp.json"
    Copy-Item -LiteralPath $StateJson -Destination $stateBackupPath -Force
}

$shadowArgs = @(
    "scripts\run_lens_penalty_shadow_v1.py",
    "--events-jsonl", $EventsJsonl,
    "--state-json", $StateJson,
    "--policy-json", $PolicyJson,
    "--out", $OutJson
)
if ($autoApplyEnabled) {
    $shadowArgs += "--apply"
}
& py @shadowArgs
$shadowExit = $LASTEXITCODE
if ($shadowExit -ne 0) { exit $shadowExit }

& py "scripts\build_lens_penalty_shadow_dashboard_v1.py" `
    --daily-json $OutJson `
    --state-json $StateJson `
    --out "docs\final\artifacts\lens_penalty_shadow_dashboard_latest.json"
$dashboardExit = $LASTEXITCODE
if ($dashboardExit -ne 0) { exit $dashboardExit }

& py "scripts\build_lens_penalty_shadow_weekly_report_v1.py" `
    --events-jsonl $EventsJsonl `
    --window-days $WeeklyWindowDays `
    --out $WeeklyOutJson
$weeklyExit = $LASTEXITCODE
if ($weeklyExit -ne 0) { exit $weeklyExit }

& py "scripts\build_lens_penalty_shadow_fail_reason_report_v1.py" `
    --events-jsonl $EventsJsonl `
    --window-days $WeeklyWindowDays `
    --out "docs\final\artifacts\lens_penalty_shadow_fail_reason_report_latest.json"
$failReasonExit = $LASTEXITCODE
if ($failReasonExit -ne 0) { exit $failReasonExit }

& py "scripts\build_lens_penalty_direction_sensitivity_sweep_v1.py" `
    --events-jsonl $EventsJsonl `
    --window-days $WeeklyWindowDays `
    --out "docs\final\artifacts\lens_penalty_direction_sensitivity_sweep_latest.json"
$sweepExit = $LASTEXITCODE
if ($sweepExit -ne 0) { exit $sweepExit }

& py "scripts\build_lens_penalty_s1_shadow_comparator_v1.py" `
    --weekly-json $WeeklyOutJson `
    --sweep-json "docs\final\artifacts\lens_penalty_direction_sensitivity_sweep_latest.json" `
    --out "docs\final\artifacts\lens_penalty_s1_shadow_comparator_latest.json"
$comparatorExit = $LASTEXITCODE
if ($comparatorExit -ne 0) { exit $comparatorExit }

& py "scripts\build_lens_penalty_s1_shadow_gate_v1.py" `
    --comparator-json "docs\final\artifacts\lens_penalty_s1_shadow_comparator_latest.json" `
    --apply-policy-json "docs\final\artifacts\lens_penalty_apply_mode_policy_v1.json" `
    --out "docs\final\artifacts\lens_penalty_s1_shadow_gate_latest.json"
$s1GateExit = $LASTEXITCODE
if ($s1GateExit -ne 0) { exit $s1GateExit }

$s1GateJsonAbsEarly = (Resolve-Path -LiteralPath "docs\final\artifacts\lens_penalty_s1_shadow_gate_latest.json").Path
$s1GateEarly = Get-Content -LiteralPath $s1GateJsonAbsEarly -Raw | ConvertFrom-Json
$gateHistoryPath = "reports\lens_penalty_s1_shadow_gate_history.jsonl"
$gateHistoryRow = [ordered]@{
    schema = "lens_penalty_s1_shadow_gate_history_row_v1"
    timestamp_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    decision = $s1GateEarly.decision
    simulated_strict_gap = $s1GateEarly.snapshot.simulated_strict_gap
    flip_candidates = $s1GateEarly.snapshot.flip_candidates
}
$gateHistoryRowJson = $gateHistoryRow | ConvertTo-Json -Compress
Add-Content -LiteralPath $gateHistoryPath -Value $gateHistoryRowJson

& py "scripts\build_lens_penalty_s1_shadow_streak_gate_v1.py" `
    --history-jsonl "reports\lens_penalty_s1_shadow_gate_history.jsonl" `
    --required-streak 2 `
    --out "docs\final\artifacts\lens_penalty_s1_shadow_streak_gate_latest.json"
$streakGateExit = $LASTEXITCODE
if ($streakGateExit -ne 0) { exit $streakGateExit }

& py "scripts\build_lens_penalty_s1_promotion_review_packet_v1.py" `
    --out "docs\final\artifacts\lens_penalty_s1_promotion_review_packet_latest.json"
$reviewPacketExit = $LASTEXITCODE
if ($reviewPacketExit -ne 0) { exit $reviewPacketExit }

& py "scripts\build_lens_penalty_s1_manual_signoff_worksheet_v1.py" `
    --out "docs\final\artifacts\lens_penalty_s1_manual_signoff_worksheet_latest.json"
$manualWorksheetExit = $LASTEXITCODE
if ($manualWorksheetExit -ne 0) { exit $manualWorksheetExit }

& py "scripts\build_lens_penalty_apply_mode_checklist_v1.py"
$applyChecklistExit = $LASTEXITCODE
if ($applyChecklistExit -ne 0) { exit $applyChecklistExit }

& py "scripts\build_lens_penalty_auto_apply_guardrail_v1.py" `
    --daily-json $OutJson `
    --weekly-json $WeeklyOutJson `
    --history-jsonl "reports\lens_penalty_auto_apply_guardrail_history.jsonl" `
    --out "docs\final\artifacts\lens_penalty_auto_apply_guardrail_latest.json"
$guardrailExit = $LASTEXITCODE
if ($guardrailExit -ne 0) { exit $guardrailExit }

$guardrailJsonAbs = (Resolve-Path -LiteralPath "docs\final\artifacts\lens_penalty_auto_apply_guardrail_latest.json").Path
$guardrail = Get-Content -LiteralPath $guardrailJsonAbs -Raw | ConvertFrom-Json
$shouldRollback = [bool]$guardrail.should_rollback
if ($autoApplyEnabled -and $shouldRollback) {
    if (-not [string]::IsNullOrWhiteSpace($stateBackupPath) -and (Test-Path -LiteralPath $stateBackupPath)) {
        Copy-Item -LiteralPath $stateBackupPath -Destination $StateJson -Force
    }
    if (Test-Path -LiteralPath $ApplyPolicyJson) {
        $policyPathAbs = (Resolve-Path -LiteralPath $ApplyPolicyJson).Path
        & py -c "import json, pathlib; p=pathlib.Path(r'$policyPathAbs'); d=json.loads(p.read_text(encoding='utf-8')); d['auto_apply_enabled']=False; p.write_text(json.dumps(d, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')"
    }
    $autoApplyEnabled = $false
}

$dailyJsonAbs = (Resolve-Path -LiteralPath $OutJson).Path
$daily = Get-Content -LiteralPath $dailyJsonAbs -Raw | ConvertFrom-Json
$summary = $daily.summary
$weeklyJsonAbs = (Resolve-Path -LiteralPath $WeeklyOutJson).Path
$weekly = Get-Content -LiteralPath $weeklyJsonAbs -Raw | ConvertFrom-Json
$weeklySummary = $weekly.summary
$failReasonJsonAbs = (Resolve-Path -LiteralPath "docs\final\artifacts\lens_penalty_shadow_fail_reason_report_latest.json").Path
$failReason = Get-Content -LiteralPath $failReasonJsonAbs -Raw | ConvertFrom-Json
$failReasonSummary = $failReason.summary
$sweepJsonAbs = (Resolve-Path -LiteralPath "docs\final\artifacts\lens_penalty_direction_sensitivity_sweep_latest.json").Path
$sweep = Get-Content -LiteralPath $sweepJsonAbs -Raw | ConvertFrom-Json
$sweepSummary = $sweep.summary
$comparatorJsonAbs = (Resolve-Path -LiteralPath "docs\final\artifacts\lens_penalty_s1_shadow_comparator_latest.json").Path
$comparator = Get-Content -LiteralPath $comparatorJsonAbs -Raw | ConvertFrom-Json
$comparatorSummary = $comparator.summary
$s1GateJsonAbs = (Resolve-Path -LiteralPath "docs\final\artifacts\lens_penalty_s1_shadow_gate_latest.json").Path
$s1Gate = Get-Content -LiteralPath $s1GateJsonAbs -Raw | ConvertFrom-Json
$streakJsonAbs = (Resolve-Path -LiteralPath "docs\final\artifacts\lens_penalty_s1_shadow_streak_gate_latest.json").Path
$streak = Get-Content -LiteralPath $streakJsonAbs -Raw | ConvertFrom-Json
$streakSnapshot = $streak.snapshot
$manualWorksheetJsonAbs = (Resolve-Path -LiteralPath "docs\final\artifacts\lens_penalty_s1_manual_signoff_worksheet_latest.json").Path
$manualWorksheet = Get-Content -LiteralPath $manualWorksheetJsonAbs -Raw | ConvertFrom-Json
$applyChecklistJsonAbs = (Resolve-Path -LiteralPath "docs\final\artifacts\lens_penalty_apply_mode_checklist_latest.json").Path
$applyChecklist = Get-Content -LiteralPath $applyChecklistJsonAbs -Raw | ConvertFrom-Json
$guardrailSummary = $guardrail.snapshot
$noteObj = [ordered]@{
    mode = $daily.mode
    applied = $daily.applied
    lenses_evaluated = $summary.lenses_evaluated
    recommendations_with_penalty = $summary.recommendations_with_penalty
    recommendations_with_recovery = $summary.recommendations_with_recovery
    weekly_events = $weeklySummary.total_events
    weekly_fail_rate = $weeklySummary.overall_fail_rate
    weekly_strict_gap = $weeklySummary.strict_gap
    fail_top_reason = $failReasonSummary.top_reason_code
    sweep_flip_candidates = $sweepSummary.flip_candidates
    comparator_simulated_strict_gap = $comparatorSummary.simulated_strict_gap
    comparator_delta_strict_gap = $comparatorSummary.delta_strict_gap
    s1_shadow_gate_decision = $s1Gate.decision
    streak_go_days = $streakSnapshot.current_go_streak
    streak_ready = $streak.all_green
    s1_manual_signoff_decision = $manualWorksheet.decision
    auto_apply_enabled = $autoApplyEnabled
    auto_apply_guardrail_decision = $guardrail.decision
    auto_apply_guardrail_rollback = $shouldRollback
    auto_apply_guardrail_strict_gap = $guardrailSummary.strict_gap
    apply_check_decision = $applyChecklist.decision
}
$noteJson = $noteObj | ConvertTo-Json -Compress

& py "scripts\log_agent_decision.py" `
    --mission-id "myeongni-penalty-shadow-daily" `
    --stage "verify" `
    --decision "penalty_shadow_daily_completed" `
    --evidence-path $dailyJsonAbs `
    --actor "Run-LensPenaltyShadowDaily_v1.ps1" `
    --risk-level "L1" `
    --retry-count 0 `
    --note $noteJson
exit $LASTEXITCODE
