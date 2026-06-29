#Requires -Version 5.1
<#
.SYNOPSIS
  A-code 12AI governor research lane smoke (RQ-028/031 · [HYPO]) — pytest only, CI-friendly.

.EXAMPLE
  pwsh -File scripts/Invoke-ACodeGovernorSmoke_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

$tests = @(
    "tests/test_a_code_12ai_matrix_v2.py"
    "tests/test_a_code_governor_knob_sim_stub_v1.py"
    "tests/test_a_code_governor_knob_multiday_replay_v1.py"
    "tests/test_a_code_commander_profile_resolve_v1.py"
    "tests/test_a_code_governor_knob_evening_observation_v1.py"
    "tests/test_a_code_governor_promotion_gate_v1.py"
    "tests/test_validate_commander_profile_v1.py"
    "tests/test_validate_commander_a_code_signoff_v1.py"
    "tests/test_a_code_promotion_checklist_readiness_v1.py"
    "tests/test_a_code_governor_trackc_dashboard_slice_v1.py"
    "tests/test_a_code_operator_assist_lane_v1.py"
    "tests/test_build_a_code_constitution_pointer_pr_draft_v1.py"
    "tests/test_check_a_code_constitution_pointer_row_v1.py"
    "tests/test_build_a_code_promotion_rq_readiness_v1.py"
    "tests/test_validate_commander_a_code_promotion_rq_ack_v1.py"
    "tests/test_dispatch_a_code_promotion_discussion_hint_v1.py"
    "tests/test_build_a_code_governor_signoff_archive_pack_v1.py"
    "tests/test_check_a_code_rq_close_gate_v1.py"
    "tests/test_build_a_code_light_ops_profile_v1.py"
    "tests/test_build_a_code_rq_close_human_checklist_v1.py"
    "tests/test_record_a_code_rq_commander_close_v1.py"
    "tests/test_build_a_code_closure_readiness_v1.py"
    "tests/test_build_a_code_weekly_ops_summary_v1.py"
    "tests/test_build_a_code_research_close_migration_draft_v1.py"
)

foreach ($t in $tests) {
    if (-not (Test-Path -LiteralPath (Join-Path $WorkspaceRoot $t))) {
        throw "Missing pytest: $t"
    }
}

Write-Host "== A-code governor smoke (pytest) ==" -ForegroundColor Cyan
& $py -m pytest @tests -q --tb=short
exit $LASTEXITCODE
