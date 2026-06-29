# Spot-check MKM_WttPilot_IntakeDropWatch scheduled task (Fact-Lock).
param(
    [string]$TaskName = "MKM_WttPilot_IntakeDropWatch",
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
$expected = Join-Path $WorkspaceRoot "scripts\Invoke-WttPilotIntakeDropWatch_v1.ps1"

$t = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$info = Get-ScheduledTaskInfo -InputObject $t
$a = $t.Actions[0]
$args = [string]$a.Arguments
$ok = ($args -match "Invoke-WttPilotIntakeDropWatch_v1\.ps1")

Write-Output "task_name=$TaskName"
Write-Output ("state={0}" -f $t.State)
Write-Output ("last_run_time={0}" -f $info.LastRunTime)
Write-Output ("last_task_result={0}" -f $info.LastTaskResult)
Write-Output ("arguments={0}" -f $args)
Write-Output ("drop_watch_action_ok={0}" -f $ok)

if (-not $ok) { exit 1 }
exit 0
