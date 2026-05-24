#Requires -Version 5.1
param(
    [string]$TaskName = "MKM-Personadiary-Daily-Guide-Refresh"
)

$ErrorActionPreference = "Stop"
$t = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$i = Get-ScheduledTaskInfo -TaskName $TaskName
[PSCustomObject]@{
    task_name = $TaskName
    state     = $t.State
    next_run  = $i.NextRunTime
    last_run  = $i.LastRunTime
    last_result = $i.LastTaskResult
    action    = $t.Actions[0].Arguments
} | Format-List
