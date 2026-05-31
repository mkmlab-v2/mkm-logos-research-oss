<#
.SYNOPSIS
  Verify MKM_MissionLog_CentralHygiene_Weekly scheduled task registration.
#>
param(
    [string]$TaskName = "MKM_MissionLog_CentralHygiene_Weekly"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Invoke-MissionLogCentralHygiene_v1.ps1"

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host "FAIL: task not registered: $TaskName"
    Write-Host "Fix: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-MissionLogCentralHygieneWeeklyTask.ps1"
    exit 1
}

$info = Get-ScheduledTaskInfo -TaskName $TaskName
$action = $task.Actions[0]
$args = $action.Arguments

$ok = $true
if ($task.State -ne "Ready") {
    Write-Host "WARN: task state=$($task.State) (expected Ready)"
    $ok = $false
}
if ($action.Execute -notmatch "powershell") {
    Write-Host "FAIL: unexpected Execute=$($action.Execute)"
    $ok = $false
}
if ($args -notmatch [regex]::Escape($runner)) {
    Write-Host "FAIL: runner not in task action: $args"
    $ok = $false
}

Write-Host "task_name=$TaskName"
Write-Host "state=$($task.State)"
Write-Host "next_run=$($info.NextRunTime)"
Write-Host "last_result=$($info.LastTaskResult)"
Write-Host "action=$($action.Execute) $($args)"

if ($ok) {
    Write-Host "VERIFY: OK"
    exit 0
}
Write-Host "VERIFY: FAIL"
exit 1
