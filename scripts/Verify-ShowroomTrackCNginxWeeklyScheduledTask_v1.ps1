<#
.SYNOPSIS
  Spot-check Showroom-TrackC-Nginx-Weekly scheduled task action (Fact-Lock).
#>
[CmdletBinding()]
param(
    [string]$TaskName = "Showroom-TrackC-Nginx-Weekly",
    [string]$WorkspaceRoot = "C:\workspace"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$expectedSync = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\sync_showroom_to_vps.ps1"
$t = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$info = Get-ScheduledTaskInfo -InputObject $t
$a = $t.Actions[0]
$args = [string]$a.Arguments
$okSync = ($args -match "sync_showroom_to_vps\.ps1")
$okSnippetOnly = ($args -match "-NginxSnippetOnly")
$okApplyNginx = ($args -match "-ApplyRecommendedNginx")

Write-Output "task_name=$TaskName"
Write-Output ("state={0}" -f $t.State)
Write-Output ("last_run_time={0}" -f $info.LastRunTime)
Write-Output ("last_task_result={0}" -f $info.LastTaskResult)
Write-Output ("execute={0}" -f $a.Execute)
Write-Output ("arguments={0}" -f $args)
Write-Output ("sync_script_action_ok={0}" -f $okSync)
Write-Output ("nginx_snippet_only_ok={0}" -f $okSnippetOnly)
Write-Output ("apply_recommended_nginx_ok={0}" -f $okApplyNginx)

if (-not ($okSync -and $okSnippetOnly -and $okApplyNginx)) {
    exit 1
}
exit 0
