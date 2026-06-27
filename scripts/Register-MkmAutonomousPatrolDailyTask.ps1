#Requires -Version 5.1
<#
.SYNOPSIS
  Register daily MKM AutonomousPatrol (자율점검) Windows scheduled task.

.PARAMETER Remove
  Unregister the task.
#>
param(
    [switch]$Remove,
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_AutonomousPatrol_Daily",
    [string]$AtLocalTime = "07:30"
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\Invoke-MkmAutonomousPatrol_v1.ps1"
$log = Join-Path $WorkspaceRoot "reports\mkm_autonomous_patrol_daily.log"

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

$cmdArgs = @(
    "/c cd /d `"$WorkspaceRoot`" &&",
    "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$runner`" -ContinueOnFail >> `"$log`" 2>&1"
) -join " "

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $cmdArgs
$trigger = New-ScheduledTaskTrigger -Daily -At $AtLocalTime
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Limited -Force | Out-Null

Write-Host "Registered: $TaskName" -ForegroundColor Green
Write-Host "  Daily at $AtLocalTime (local)"
Write-Host "  Log: $log"
