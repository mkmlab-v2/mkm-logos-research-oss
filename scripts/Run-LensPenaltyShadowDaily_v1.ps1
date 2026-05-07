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
    [string]$OutJson = ""
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

& py "scripts\build_daily_execution_falsification_input_v1.py" `
    --out $InputJson

& py "scripts\build_daily_execution_falsification_events_v1.py" `
    --input-json $InputJson `
    --events-jsonl $EventsJsonl `
    --out "docs\final\artifacts\daily_execution_falsification_events_latest.json"

& py "scripts\run_lens_penalty_shadow_v1.py" `
    --events-jsonl $EventsJsonl `
    --state-json $StateJson `
    --policy-json $PolicyJson `
    --out $OutJson
$shadowExit = $LASTEXITCODE
if ($shadowExit -ne 0) { exit $shadowExit }

& py "scripts\build_lens_penalty_shadow_dashboard_v1.py" `
    --daily-json $OutJson `
    --state-json $StateJson `
    --out "docs\final\artifacts\lens_penalty_shadow_dashboard_latest.json"
$dashboardExit = $LASTEXITCODE
if ($dashboardExit -ne 0) { exit $dashboardExit }

$dailyJsonAbs = (Resolve-Path -LiteralPath $OutJson).Path
$daily = Get-Content -LiteralPath $dailyJsonAbs -Raw | ConvertFrom-Json
$summary = $daily.summary
$noteObj = [ordered]@{
    mode = $daily.mode
    applied = $daily.applied
    lenses_evaluated = $summary.lenses_evaluated
    recommendations_with_penalty = $summary.recommendations_with_penalty
    recommendations_with_recovery = $summary.recommendations_with_recovery
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
