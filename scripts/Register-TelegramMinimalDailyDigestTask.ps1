#Requires -Version 5.1
<#
.SYNOPSIS
  Daily premarket Telegram — Korean prophecy-only digest (default 08:28 KST, after 08:18 eval).

.DESCRIPTION
  Sends Invoke-TelegramMinimalDailyDigest_v1.ps1 (prophecy style only).
  No advanced briefing / personal fortune / RAG / R-IBL blocks (evening score is 20:30 JSON).
  TELEGRAM_* from .env, User env, or DPAPI (Security Agent).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$At = "08:28",
    [string]$TaskName = "MKM-Telegram-Minimal-Daily-Digest",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[REMOVED] $TaskName" -ForegroundColor Yellow
    exit 0
}

$invokeScript = Join-Path $WorkspaceRoot "scripts\Invoke-TelegramMinimalDailyDigest_v1.ps1"
if (-not (Test-Path -LiteralPath $invokeScript)) {
    throw "Missing SSOT script: $invokeScript"
}

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$invokeScript`" -WorkspaceRoot `"$WorkspaceRoot`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 15) -MultipleInstances IgnoreNew -Hidden
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
    -Description "Daily Korean prophecy-only Telegram (08:28, after eval 08:18). Style=prophecy." -Force | Out-Null

$i = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "[DONE] $TaskName at $At Next=$($i.NextRunTime)" -ForegroundColor Green
