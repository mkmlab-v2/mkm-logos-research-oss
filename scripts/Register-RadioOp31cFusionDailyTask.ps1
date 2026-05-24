<#
.SYNOPSIS
  Register daily Windows task for O-P31c fusion chain (full + health + video FIFO + RTMP cmd).

.EXAMPLE
  pwsh -File scripts\Register-RadioOp31cFusionDailyTask.ps1 -DryRun
  pwsh -File scripts\Register-RadioOp31cFusionDailyTask.ps1 -RunAt 07:12
  pwsh -File scripts\Register-RadioOp31cFusionDailyTask.ps1 -SkipRender -SkipVideoBed
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MKM-Radio-Op31c-Fusion-Daily",
    [string]$RunAt = "07:12",
    [switch]$SkipRender,
    [switch]$SkipCommanderRefresh,
    [switch]$SkipVideoBed,
    [switch]$DryRun,
    [switch]$Remove,
    [switch]$StartNow
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Chain = Join-Path $RepoRoot "scripts\Invoke-RadioOp31cFusionDailyChain_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "scheduled_task: REMOVED ($TaskName)"
    exit 0
}

$args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $Chain)
if ($SkipRender) { $args += "-SkipRender" }
if ($SkipCommanderRefresh) { $args += "-SkipCommanderRefresh" }
if ($SkipVideoBed) { $args += "-SkipVideoBed" }

$action = New-ScheduledTaskAction -Execute "pwsh.exe" -Argument ($args -join " ") -WorkingDirectory $RepoRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $RunAt
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 3)

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
