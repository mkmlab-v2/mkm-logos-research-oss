<#
.SYNOPSIS
  Print scheduled-task action for MKM_Mkmlife_NewsObservationFusion_Daily (Fact-Lock spot check).

.NOTES
  Re-register flags with scripts/Register-MkmlifeNewsObservationFusionDailyTask.ps1 (same -TaskName overwrites).
  deploy_in_action=True means -DeployMkmlifeAssets was registered (asset-only wrangler deploy).
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MKM_Mkmlife_NewsObservationFusion_Daily"
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
Write-Output ("next_run_time={0}" -f $info.NextRunTime)
Write-Output ("execute={0}" -f $a.Execute)
Write-Output ("arguments={0}" -f $a.Arguments)
Write-Output ("working_directory={0}" -f $a.WorkingDirectory)
Write-Output ("deploy_in_action={0}" -f ($a.Arguments -match '-DeployMkmlifeAssets'))
Write-Output ("fetch_rss_in_action={0}" -f ($a.Arguments -match '-FetchRss'))
