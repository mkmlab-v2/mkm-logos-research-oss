# Register weekly Logos passive drift governance (--fast)
param(
    [string]$WeeklyAt = "Sun 09:00"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$taskName = "MKM_LogosPassiveDriftWeekly_v1"
$script = Join-Path $root "scripts\Run-LogosPassiveDriftGovernanceChain_v1.ps1"
$action = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$script`""

$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $WeeklyAt.Split(" ")[1]
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName $taskName -Action (New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`"") -Trigger $trigger -Settings $settings -Description "Logos passive drift --fast; NON_GATING B-track only"
Write-Host "Registered: $taskName at $WeeklyAt"
