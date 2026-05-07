<#
.SYNOPSIS
  Append daily execution falsification events from operator input JSON.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$InputJson = "",
    [string]$EventsJsonl = "",
    [string]$OutJson = ""
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

if ([string]::IsNullOrWhiteSpace($InputJson)) {
    $InputJson = "reports\daily_execution_falsification_input_latest.json"
}
if ([string]::IsNullOrWhiteSpace($EventsJsonl)) {
    $EventsJsonl = "reports\daily_execution_insight_falsification_log.jsonl"
}
if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = "docs\final\artifacts\daily_execution_falsification_events_latest.json"
}

& py "scripts\build_daily_execution_falsification_events_v1.py" `
    --input-json $InputJson `
    --events-jsonl $EventsJsonl `
    --out $OutJson
exit $LASTEXITCODE
