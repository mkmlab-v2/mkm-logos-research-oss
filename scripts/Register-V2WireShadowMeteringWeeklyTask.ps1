#Requires -Version 5.1
<#
.SYNOPSIS
  Register weekly Task Scheduler: v2 wire shadow metering (B-track; no active writes).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-V2WireShadowMeteringWeeklyTask.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-V2WireShadowMeteringWeeklyTask.ps1 -Remove
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM-V2-Wire-Shadow-Metering-Weekly",
    [string]$SundayAt = "10:15",
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$MaxCases = 0,
    [switch]$RunWhenLoggedOff
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $WorkspaceRoot "scripts\Run-V2WireShadowMeteringWeekly_v1.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[DONE] Removed: $TaskName"
    exit 0
}

$parts = $SundayAt -split ":"
$hour = [int]$parts[0]
$minute = if ($parts.Length -gt 1) { [int]$parts[1] } else { 0 }
$actionArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`" -MaxCases $MaxCases"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $actionArgs -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At ([datetime]::Today.Date.AddHours($hour).AddMinutes($minute))
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3) `
    -MultipleInstances IgnoreNew
$logonType = if ($RunWhenLoggedOff) { "S4U" } else { "Interactive" }
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType $logonType -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Write-Host "[DONE] Registered: $TaskName (Sunday $SundayAt) -> Run-V2WireShadowMeteringWeekly_v1.ps1"
exit 0
