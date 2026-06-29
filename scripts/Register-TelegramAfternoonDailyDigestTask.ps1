#Requires -Version 5.1
<#
.SYNOPSIS
  Daily afternoon Korean Telegram — fortune + KOSPI (default 18:00 KST, weekdays).

.DESCRIPTION
  Sends Invoke-TelegramAfternoonDailyDigest_v1.ps1 (afternoon style only).
  Evening 20:30 score Telegram stays OFF unless MKM_TELEGRAM_EVENING_DIGEST_ENABLED=1.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$At = "18:00",
    [string]$TaskName = "MKM-Telegram-Afternoon-Daily-Digest",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[REMOVED] $TaskName" -ForegroundColor Yellow
    exit 0
}

$invokeScript = Join-Path $WorkspaceRoot "scripts\Invoke-TelegramAfternoonDailyDigest_v1.ps1"
if (-not (Test-Path -LiteralPath $invokeScript)) {
    throw "Missing SSOT script: $invokeScript"
}

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$invokeScript`" -WorkspaceRoot `"$WorkspaceRoot`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -MultipleInstances IgnoreNew -Hidden
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
    -Description "Weekday Korean afternoon Telegram (fortune + KOSPI). Style=afternoon." -Force | Out-Null

$i = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "[DONE] $TaskName Mon-Fri at $At Next=$($i.NextRunTime)" -ForegroundColor Green
