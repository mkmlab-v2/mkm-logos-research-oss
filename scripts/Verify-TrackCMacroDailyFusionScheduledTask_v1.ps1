<#
.SYNOPSIS
  Print scheduled-task action for MKM-TrackC-MacroDailyFusion (Fact-Lock spot check).

.NOTES
  Re-register flags with scripts/Register-TrackCMacroDailyFusionTask.ps1 (same -TaskName overwrites).
  Hosts without Aramaic/morphology inputs may use -SkipLogosInsightBundle on Register so the scheduled
  task passes it through to Invoke-TrackCMacroDailyFusion_v1.ps1.
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MKM-TrackC-MacroDailyFusion"
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
