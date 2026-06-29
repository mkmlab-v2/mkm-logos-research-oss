#Requires -Version 5.1
<#
.SYNOPSIS
  Spot-check MKM_AgentHandoffGovernance_WeeklyBaseline scheduled task action.
#>
param(
    [string]$TaskName = "MKM_AgentHandoffGovernance_WeeklyBaseline"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$t = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$info = Get-ScheduledTaskInfo -InputObject $t
$a = $t.Actions[0]

Write-Output "task_name=$TaskName"
Write-Output ("state={0}" -f $t.State)
Write-Output ("last_run_time={0}" -f $info.LastRunTime)
Write-Output ("last_task_result={0}" -f $info.LastTaskResult)
Write-Output ("execute={0}" -f $a.Execute)
Write-Output ("arguments={0}" -f $a.Arguments)
Write-Output ("working_directory={0}" -f $a.WorkingDirectory)
