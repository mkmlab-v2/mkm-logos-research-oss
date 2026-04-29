param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

& py -3 "scripts/run_pre_news_shadow_holdout_lock_mismatch_drill_v1.py"
$holdoutLockExitCode = $LASTEXITCODE

& py -3 "scripts/run_pre_news_shadow_policy_governance_drill_v1.py" --threshold 2
$policyGovernanceExitCode = $LASTEXITCODE

& py -3 "scripts/alert_pre_news_shadow_monthly_drill_summary_v1.py" `
    --holdout-lock-drill-json "docs/final/artifacts/pre_news_shadow_holdout_lock_mismatch_drill_latest.json" `
    --policy-governance-drill-json "docs/final/artifacts/pre_news_shadow_policy_governance_drill_latest.json" `
    --holdout-lock-exit-code $holdoutLockExitCode `
    --policy-governance-exit-code $policyGovernanceExitCode `
    --out-alert-json "docs/final/artifacts/pre_news_shadow_monthly_drill_summary_alert_latest.json" `
    --append-log-jsonl "reports/pre_news_shadow_monthly_drill_summary_alert_log.jsonl"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (($holdoutLockExitCode -ne 0) -or ($policyGovernanceExitCode -ne 0)) {
    Write-Warning ("Monthly governance drills failed: holdout_lock={0}, policy_governance={1}" -f $holdoutLockExitCode, $policyGovernanceExitCode)
    exit 1
}

Write-Host "DONE: pre-news shadow monthly governance drills." -ForegroundColor Green

