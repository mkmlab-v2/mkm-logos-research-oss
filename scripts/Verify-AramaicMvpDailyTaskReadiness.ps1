#Requires -Version 5.1
<#
.SYNOPSIS
  Print scheduled-task action for MKM-AramaicMvp-DailyAudit (Fact-Lock spot check).

.NOTES
  Re-register flags with scripts/Register-AramaicMvpDailyTask.ps1 (same -TaskName overwrites).
  Chain-only POST skip without re-register: User/Process env MKM_ARAMAIC_SURVIVOR_HEALTH_ALERT_DRY_RUN=1|true|yes (see run_aramaic_mvp_chain_v1.ps1).
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MKM-AramaicMvp-DailyAudit"
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
$drySwitch = $false
if ($argStr -match '(^|\s)-SurvivorHealthAlertDryRun(\s|$)') { $drySwitch = $true }
Write-Output ("survivor_health_alert_dry_run_switch_in_task_action={0}" -f $drySwitch)
