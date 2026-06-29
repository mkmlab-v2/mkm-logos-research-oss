<#
.SYNOPSIS
  Verify MKM_BiblicalHistory_WeeklyMaintenance scheduled task registration.
#>
param(
    [string]$TaskName = "MKM_BiblicalHistory_WeeklyMaintenance",
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
$expectedRunner = Join-Path $WorkspaceRoot "scripts\run_biblical_history_weekly_maintenance_v1.py"
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Output (@{ ok = $false; task_name = $TaskName; error = "task_not_registered" } | ConvertTo-Json -Compress)
    exit 1
}

$info = Get-ScheduledTaskInfo -TaskName $TaskName
$action = ($task.Actions | Select-Object -First 1)
$args = [string]$action.Arguments
$ok = ($action.Execute -match '^py(\.exe)?$') -and ($args -like "*run_biblical_history_weekly_maintenance_v1.py*")

Write-Output (@{
    ok = $ok
    task_name = $TaskName
    state = [string]$task.State
    next_run_time = if ($info.NextRunTime) { $info.NextRunTime.ToString("o") } else { $null }
    action_execute = [string]$action.Execute
    action_arguments = $args
    expected_runner = $expectedRunner
} | ConvertTo-Json -Compress)

if (-not $ok) { exit 1 }
