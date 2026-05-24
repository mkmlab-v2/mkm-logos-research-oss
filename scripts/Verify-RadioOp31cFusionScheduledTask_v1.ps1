<#
.SYNOPSIS
  Spot-check MKM-Radio-Op31c-Fusion-Daily scheduled task action and RTMP env.

.EXAMPLE
  pwsh -File scripts\Verify-RadioOp31cFusionScheduledTask_v1.ps1
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MKM-Radio-Op31c-Fusion-Daily"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$t = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$info = Get-ScheduledTaskInfo -InputObject $t
$a = $t.Actions[0]

$rtmpSet = [bool]($env:YOUTUBE_RTMP_URL -and $env:YOUTUBE_RTMP_URL.Trim())
$fusionInArgs = $a.Arguments -match "Invoke-RadioOp31cFusionDailyChain"

Write-Output "task_name=$TaskName"
Write-Output ("state={0}" -f $t.State)
Write-Output ("last_run_time={0}" -f $info.LastRunTime)
Write-Output ("last_task_result={0}" -f $info.LastTaskResult)
Write-Output ("execute={0}" -f $a.Execute)
Write-Output ("arguments={0}" -f $a.Arguments)
Write-Output ("working_directory={0}" -f $a.WorkingDirectory)
Write-Output ("fusion_chain_in_action={0}" -f $fusionInArgs)
Write-Output ("youtube_rtmp_url_configured={0}" -f $rtmpSet)
if (-not $rtmpSet) {
    Write-Output "hint=Set User env YOUTUBE_RTMP_URL for Zone A live push (command file still generated)"
}
