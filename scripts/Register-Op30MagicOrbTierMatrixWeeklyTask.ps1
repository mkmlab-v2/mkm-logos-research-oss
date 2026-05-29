#Requires -Version 5.1
<#
.SYNOPSIS
  Register weekly O-P30 multilens tier-matrix smoke (entry/standard/premium on mkmlife.com).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Op30_MagicOrb_TierMatrix_Weekly",
    [string]$WeeklyAt = "08:15",
    [ValidateSet("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")]
    [string]$DayOfWeek = "Sunday"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Invoke-Op30MagicOrbWeeklyTierMatrix_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$dow = [System.DayOfWeek]::$DayOfWeek
$parts = $WeeklyAt -split ':'
$at = Get-Date -Hour ([int]$parts[0]) -Minute ([int]$parts[1]) -Second 0
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`"" `
    -WorkingDirectory $workspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $dow -At $at
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 35)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "O-P30 weekly: multilens tier-matrix + preview smoke on mkmlife.com. [HYPO] B-track."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered: $TaskName $DayOfWeek at $WeeklyAt"
Write-Host "Verify: powershell -File scripts\Verify-Op30MagicOrbTierMatrixWeeklyTask_v1.ps1"
Write-Host "Remove: powershell -File scripts\Register-Op30MagicOrbTierMatrixWeeklyTask.ps1 -Remove"
