#Requires -Version 5.1
<#
.SYNOPSIS
  Pre-News shadow: projection run + weekly report + policy governance + ops dashboard.
.NOTES
  research_only; does not enable live trading.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipProjectionRun
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Test-Path "$env:WINDIR\py.exe") { "$env:WINDIR\py.exe" } else { "py" }

if (-not $SkipProjectionRun) {
    & $py scripts/run_global_atom_pre_news_shadow_chain_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& $py scripts/build_global_atom_pre_news_shadow_weekly_report_v1.py `
    --log-jsonl reports/pre_news_shadow_projection_log.jsonl `
    --holdout-dataset-lock-json docs/final/artifacts/global_atom_news_holdout_dataset_lock_manifest_v1.json `
    --enforce-holdout-dataset-lock `
    --stage-threshold-policy-json docs/final/artifacts/pre_news_shadow_stage_threshold_policy_v1.json `
    --enforce-policy-effective-from `
    --window-days 7
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $py scripts/build_pre_news_shadow_policy_change_audit_summary_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $py scripts/alert_pre_news_shadow_policy_governance_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $py scripts/build_pre_news_shadow_ops_status_dashboard_v1.py
exit $LASTEXITCODE
