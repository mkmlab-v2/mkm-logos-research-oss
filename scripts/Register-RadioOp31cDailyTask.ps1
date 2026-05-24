<#
.SYNOPSIS
  Register daily Windows task for O-P31c full chain (commander SSOT + Zone A/B).

.EXAMPLE
  pwsh -File scripts\Register-RadioOp31cDailyTask.ps1 -DryRun
  pwsh -File scripts\Register-RadioOp31cDailyTask.ps1 -RunAt 07:10
  pwsh -File scripts\Register-RadioOp31cDailyTask.ps1 -SkipRender
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MKM-Radio-Op31c-Daily",
    [string]$RunAt = "07:10",
    [switch]$SkipRender,
    [switch]$SkipCommanderRefresh,
    [switch]$DryRun,
    [switch]$Remove,
    [switch]$StartNow
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Chain = Join-Path $RepoRoot "scripts\Invoke-RadioOp31cFullDailyChain_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "scheduled_task: REMOVED ($TaskName)"
    exit 0
}

$args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $Chain)
if ($SkipRender) { $args += "-SkipRender" }
if ($SkipCommanderRefresh) { $args += "-SkipCommanderRefresh" }

$action = New-ScheduledTaskAction -Execute "pwsh.exe" -Argument ($args -join " ") -WorkingDirectory $RepoRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $RunAt
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

if ($DryRun) {
    Write-Output "scheduled_task: PLANNED ($TaskName) at $RunAt"
    Write-Output "  action: pwsh $($args -join ' ')"
    exit 0
}

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Write-Output "scheduled_task: REGISTERED ($TaskName) daily $RunAt"

if ($StartNow) {
    Start-ScheduledTask -TaskName $TaskName
    Write-Output "scheduled_task: STARTED ($TaskName)"
}
