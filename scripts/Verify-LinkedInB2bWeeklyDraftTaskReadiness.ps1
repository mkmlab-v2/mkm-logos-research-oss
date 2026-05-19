#Requires -Version 5.1
<#
.SYNOPSIS
  Print scheduled-task action for MKM_LinkedIn_B2B_WeeklyDraft (Fact-Lock spot check).
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MKM_LinkedIn_B2B_WeeklyDraft"
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
$argStr = [string]$a.Arguments
$hasRunner = $argStr -match 'run_linkedin_b2b_weekly_draft_chain_v1\.ps1'
Write-Output ("weekly_draft_chain_in_task_action={0}" -f $hasRunner)
