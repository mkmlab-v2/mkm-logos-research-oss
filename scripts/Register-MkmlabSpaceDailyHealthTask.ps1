<#
.SYNOPSIS
  Register daily Task Scheduler job: mkmlab CF zone poll + probe.

.NOTES
  Disable after reports show zone_status=active for 2+ days:
    Unregister-ScheduledTask -TaskName MKM_MkmlabSpace_DailyHealth -Confirm:$false
#>
param(
    [string]$TaskName = "MKM_MkmlabSpace_DailyHealth",
    [string]$RunAt = "08:15",
    [switch]$Unregister,
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$runner = Join-Path $root "scripts\Invoke-MkmlabSpaceDailyHealth_v1.ps1"
$action = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$runner`""

if ($Unregister) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Unregistered $TaskName"
    exit 0
}

if ($WhatIfOnly) {
    Write-Host "Would register: $TaskName at $RunAt -> $runner"
    exit 0
}

$exists = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($exists) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

$trigger = New-ScheduledTaskTrigger -Daily -At $RunAt
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action (New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runner`"") -Trigger $trigger -Settings $settings -Principal $principal | Out-Null
Write-Host "Registered $TaskName daily $RunAt"
exit 0
