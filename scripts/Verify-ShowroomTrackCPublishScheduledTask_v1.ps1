<#
.SYNOPSIS
  Spot-check Showroom-TrackC-Publish-Daily scheduled task action (Fact-Lock).
#>
[CmdletBinding()]
param(
    [string]$TaskName = "Showroom-TrackC-Publish-Daily",
    [string]$WorkspaceRoot = "C:\workspace"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$expectedRoutine = Join-Path $WorkspaceRoot "scripts\Invoke-ShowroomTrackCPublishRoutine_v1.ps1"
$t = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$info = Get-ScheduledTaskInfo -InputObject $t
$a = $t.Actions[0]
$args = [string]$a.Arguments
$ok = ($args -match "Invoke-ShowroomTrackCPublishRoutine_v1\.ps1")

Write-Output "task_name=$TaskName"
Write-Output ("state={0}" -f $t.State)
Write-Output ("last_run_time={0}" -f $info.LastRunTime)
Write-Output ("last_task_result={0}" -f $info.LastTaskResult)
Write-Output ("execute={0}" -f $a.Execute)
Write-Output ("arguments={0}" -f $args)
Write-Output ("publish_routine_action_ok={0}" -f $ok)

if (-not $ok) {
    exit 1
}
exit 0
