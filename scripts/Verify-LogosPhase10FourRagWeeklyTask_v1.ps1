# Verify MKM_Logos_Phase10_FourRag_Weekly scheduled task registration
param(
    [string]$TaskName = "MKM_Logos_Phase10_FourRag_Weekly"
)

$ErrorActionPreference = "Stop"
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Error "Task not found: $TaskName"
    exit 1
}

$info = Get-ScheduledTaskInfo -TaskName $TaskName
$action = $task.Actions | Select-Object -First 1
Write-Host "task_name=$TaskName"
Write-Host "state=$($task.State)"
Write-Host "next_run=$($info.NextRunTime)"
Write-Host "last_run=$($info.LastRunTime)"
Write-Host "last_result=$($info.LastTaskResult)"
Write-Host "action=$($action.Execute) $($action.Arguments)"

if ($task.State -ne "Ready") {
    Write-Error "Task state is not Ready: $($task.State)"
    exit 1
}

if ($action.Arguments -notmatch "Run-LogosPhase10FourRagEnvelopeRefresh_v1\.ps1") {
    Write-Error "Unexpected action arguments"
    exit 1
}

Write-Host "verify_ok=true"
exit 0
