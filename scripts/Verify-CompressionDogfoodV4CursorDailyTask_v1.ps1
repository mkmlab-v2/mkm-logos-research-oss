<#
.SYNOPSIS
  Verify readiness for compression dogfood v4 cursor daily task.

.DESCRIPTION
  Checks:
  - Scheduled task registration/status/next run/last result
  - Runner script existence
  - Latest auto-chain status artifact presence and summary
#>
param(
    [string]$TaskName = "MKM_Compression_Dogfood_V4_Cursor_Daily",
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$AsJson
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path

$runner = Join-Path $WorkspaceRoot "scripts\Run-CompressionDogfoodV4CursorAutoChain_v1.ps1"
$statusPath = Join-Path $WorkspaceRoot "reports\compression_dogfood_v4_cursor_auto_chain_latest.json"

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
$taskInfo = $null
if ($task) {
    $taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
}

$statusJson = $null
if (Test-Path -LiteralPath $statusPath) {
    try {
        $statusJson = Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json
    } catch {
        $statusJson = $null
    }
}

$result = [ordered]@{
    schema = "verify_compression_dogfood_v4_cursor_daily_task_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    task_name = $TaskName
    checks = [ordered]@{
        task_registered = [bool]$task
        task_state = if ($task) { $task.State.ToString() } else { "MISSING" }
        next_run_time = if ($taskInfo) { $taskInfo.NextRunTime } else { $null }
        last_run_time = if ($taskInfo) { $taskInfo.LastRunTime } else { $null }
        last_task_result = if ($taskInfo) { $taskInfo.LastTaskResult } else { $null }
        runner_exists = Test-Path -LiteralPath $runner
        status_artifact_exists = Test-Path -LiteralPath $statusPath
        latest_status_ok = if ($statusJson) { [bool]$statusJson.ok } else { $null }
        latest_status_exit_code = if ($statusJson) { $statusJson.exit_code } else { $null }
    }
}

$checks = $result.checks
$ready = (
    $checks.task_registered -and
    $checks.runner_exists -and
    $checks.status_artifact_exists -and
    ($null -ne $checks.latest_status_ok)
)
$result["ready"] = [bool]$ready
$result["note"] = "B-track research_only daily automation. SEND_GATE expected HOLD."

if ($AsJson) {
    $result | ConvertTo-Json -Depth 6
    exit 0
}

Write-Host "=== Verify Compression Dogfood V4 Cursor Daily Task ===" -ForegroundColor Cyan
Write-Host ("task_registered      : {0}" -f $checks.task_registered)
Write-Host ("task_state           : {0}" -f $checks.task_state)
Write-Host ("next_run_time        : {0}" -f $checks.next_run_time)
Write-Host ("last_run_time        : {0}" -f $checks.last_run_time)
Write-Host ("last_task_result     : {0}" -f $checks.last_task_result)
Write-Host ("runner_exists        : {0}" -f $checks.runner_exists)
Write-Host ("status_artifact      : {0}" -f $checks.status_artifact_exists)
Write-Host ("latest_status_ok     : {0}" -f $checks.latest_status_ok)
Write-Host ("latest_status_exit   : {0}" -f $checks.latest_status_exit_code)
Write-Host ("ready                : {0}" -f $result.ready) -ForegroundColor Green
Write-Host $result.note -ForegroundColor DarkYellow
exit 0

