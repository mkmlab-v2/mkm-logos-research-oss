# Verify MKM-PatientIntakeFusion-Weekly scheduled task registration.
param(
    [string]$TaskName = "MKM-PatientIntakeFusion-Weekly",
    [string]$ExpectedScriptLeaf = "Run-PatientIntakeFusionBtrackWeeklyOps_v1.ps1"
)
$ErrorActionPreference = "Stop"
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Output @{ ok = $false; task_name = $TaskName; error = "task_not_found" } | ConvertTo-Json -Compress
    exit 1
}
$info = Get-ScheduledTaskInfo -TaskName $TaskName
$action = ($task.Actions | Select-Object -First 1)
$arg = [string]$action.Arguments
$ok = $arg -match [regex]::Escape($ExpectedScriptLeaf)
$out = @{
    ok = $ok
    task_name = $TaskName
    state = [string]$task.State
    last_result = $info.LastTaskResult
    next_run = $info.NextRunTime
    arguments_contain_weekly_ops = $ok
    arguments = $arg
}
$out | ConvertTo-Json -Compress
if (-not $ok) { exit 1 }
exit 0
