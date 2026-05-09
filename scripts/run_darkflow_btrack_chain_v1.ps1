param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$BaseEvalJson = "docs/final/artifacts/darkflow_btrack_eval_template_v1.json",
  [string]$OverrideJson = "docs/final/artifacts/darkflow_notebooklm_override_template_v1.json",
  [string]$EvalLatestJson = "docs/final/artifacts/darkflow_btrack_eval_latest.json",
  [ValidateSet("dotenv", "user", "process")]
  [string]$EnvSourceMode = "dotenv",
  [switch]$EnableAutoProfileSwitch,
  [switch]$SkipNotebooklmOverride
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

$env:DARKFLOW_ENV_SOURCE_MODE = $EnvSourceMode
Write-Host "Darkflow env source mode: $EnvSourceMode"

if (-not $SkipNotebooklmOverride) {
  Write-Host "==> apply_darkflow_notebooklm_overrides_v1.py"
  py scripts/apply_darkflow_notebooklm_overrides_v1.py `
    --base-json $BaseEvalJson `
    --override-json $OverrideJson `
    --output-json $EvalLatestJson
  if ($LASTEXITCODE -ne 0) { throw "apply_darkflow_notebooklm_overrides_v1.py exit $LASTEXITCODE" }
} else {
  Write-Host "Skip NotebookLM overrides (-SkipNotebooklmOverride)." -ForegroundColor DarkYellow
  $EvalLatestJson = $BaseEvalJson
}

Write-Host "==> check_darkflow_btrack_gate_v1.py"
py scripts/check_darkflow_btrack_gate_v1.py --eval-json $EvalLatestJson
if ($LASTEXITCODE -ne 0) { throw "check_darkflow_btrack_gate_v1.py exit $LASTEXITCODE" }

Write-Host "==> build_darkflow_btrack_brief_v1.py"
py scripts/build_darkflow_btrack_brief_v1.py
if ($LASTEXITCODE -ne 0) { throw "build_darkflow_btrack_brief_v1.py exit $LASTEXITCODE" }

Write-Host "==> build_darkflow_btrack_dual_policy_report_v1.py"
py scripts/build_darkflow_btrack_dual_policy_report_v1.py --eval-json $EvalLatestJson
if ($LASTEXITCODE -ne 0) { throw "build_darkflow_btrack_dual_policy_report_v1.py exit $LASTEXITCODE" }

Write-Host "==> build_darkflow_btrack_status_snapshot_v1.py"
py scripts/build_darkflow_btrack_status_snapshot_v1.py
if ($LASTEXITCODE -ne 0) { throw "build_darkflow_btrack_status_snapshot_v1.py exit $LASTEXITCODE" }

Write-Host "==> build_darkflow_ops_truth_panel_v1.py"
py scripts/build_darkflow_ops_truth_panel_v1.py
if ($LASTEXITCODE -ne 0) { throw "build_darkflow_ops_truth_panel_v1.py exit $LASTEXITCODE" }

Write-Host "==> append_darkflow_ops_history_v1.py"
py scripts/append_darkflow_ops_history_v1.py
if ($LASTEXITCODE -ne 0) { throw "append_darkflow_ops_history_v1.py exit $LASTEXITCODE" }

Write-Host "==> build_darkflow_ops_trend_summary_v1.py"
py scripts/build_darkflow_ops_trend_summary_v1.py
if ($LASTEXITCODE -ne 0) { throw "build_darkflow_ops_trend_summary_v1.py exit $LASTEXITCODE" }

if ($EnableAutoProfileSwitch) {
  Write-Host "==> auto_switch_darkflow_weekly_profile_v1.py (--apply)"
  py scripts/auto_switch_darkflow_weekly_profile_v1.py --apply
  if ($LASTEXITCODE -ne 0) { throw "auto_switch_darkflow_weekly_profile_v1.py exit $LASTEXITCODE" }
} else {
  Write-Host "Skip weekly profile auto-switch (use -EnableAutoProfileSwitch to apply)." -ForegroundColor DarkYellow
}

Write-Host "==> build_darkflow_weekly_governance_decision_v1.py"
py scripts/build_darkflow_weekly_governance_decision_v1.py
if ($LASTEXITCODE -ne 0) { throw "build_darkflow_weekly_governance_decision_v1.py exit $LASTEXITCODE" }

Write-Host "OK: darkflow B-track chain finished."
