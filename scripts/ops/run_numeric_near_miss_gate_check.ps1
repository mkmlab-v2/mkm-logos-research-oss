param(
    [string]$WorkflowId = "253106556",
    [string]$Ref = "main",
    [switch]$ApproveNumericNearMiss,
    [int]$WatchIntervalSec = 5
)

$ErrorActionPreference = "Stop"

function Write-Section([string]$Title) {
    Write-Host ""
    Write-Host "=== $Title ===" -ForegroundColor Cyan
}

$approveValue = if ($ApproveNumericNearMiss.IsPresent) { "true" } else { "false" }

Write-Section "Dispatch workflow"
$dispatchUrl = gh workflow run $WorkflowId --ref $Ref -f "approve_numeric_near_miss=$approveValue"
if ([string]::IsNullOrWhiteSpace($dispatchUrl)) {
    throw "Failed to dispatch workflow id=$WorkflowId"
}
Write-Host "dispatch_url=$dispatchUrl"

Write-Section "Resolve latest run id"
$runId = gh run list --workflow $WorkflowId --limit 1 --json databaseId --jq ".[0].databaseId"
if ([string]::IsNullOrWhiteSpace($runId)) {
    throw "Could not resolve latest run id after dispatch"
}
Write-Host "run_id=$runId"

Write-Section "Watch run"
gh run watch $runId --interval $WatchIntervalSec --exit-status

Write-Section "Extract gate verdict from logs"
$logText = gh run view $runId --log
$verdictLine = $logText | Select-String -Pattern "approved=.+promoted="
$flagLine = $logText | Select-String -Pattern "--approval-flag"
if (-not $verdictLine) {
    throw "Could not find approval/promotion verdict in run log."
}
if (-not $flagLine) {
    throw "Could not find approval flag invocation in run log."
}

Write-Host $verdictLine
Write-Host $flagLine

Write-Section "Run summary"
gh run view $runId --json status,conclusion,url,displayTitle

Write-Host ""
Write-Host "OK: numeric near-miss gate check completed (approve=$approveValue, run_id=$runId)" -ForegroundColor Green
