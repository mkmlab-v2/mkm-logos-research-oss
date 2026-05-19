#Requires -Version 5.1
<#
.SYNOPSIS
  Spot-check MKM_Marketing_WeeklyDraftBundle scheduled task (no -Gemini in default action).
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MKM_Marketing_WeeklyDraftBundle"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$t = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$info = Get-ScheduledTaskInfo -InputObject $t
$a = $t.Actions[0]
$argStr = [string]$a.Arguments

Write-Output "task_name=$TaskName"
Write-Output ("state={0}" -f $t.State)
Write-Output ("last_run_time={0}" -f $info.LastRunTime)
Write-Output ("last_task_result={0}" -f $info.LastTaskResult)
Write-Output ("arguments={0}" -f $argStr)
$hasBundle = $argStr -match 'Run-MarketingWeeklyDraftBundle_v1\.ps1'
$hasGemini = $argStr -match '\-Gemini'
Write-Output ("marketing_weekly_bundle_in_task_action={0}" -f $hasBundle)
Write-Output ("gemini_flag_in_task_action={0}" -f $hasGemini)
if ($hasGemini) {
    Write-Warning "Task action includes -Gemini; tier_0 recommends removing it from scheduled args."
}
