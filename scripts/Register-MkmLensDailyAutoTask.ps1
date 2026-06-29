#Requires -Version 5.1
<#
.SYNOPSIS
  Register daily MKM lens auto (OOS promote + 10lane + hardening). Telegram four_lens off by default.

.PARAMETER At
  Local time (default 08:25, before 08:28 digest).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$At = "08:25",
    [string]$TaskName = "MKM-Lens-Daily-Auto",
    [switch]$SendTelegram,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$invokeScript = Join-Path $WorkspaceRoot "scripts\Invoke-MkmLensDailyAuto_v1.ps1"
if (-not (Test-Path -LiteralPath $invokeScript)) {
    throw "Missing: $invokeScript"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[REMOVED] $TaskName" -ForegroundColor Yellow
    exit 0
}

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$invokeScript`" -WorkspaceRoot `"$WorkspaceRoot`""
if (-not $SendTelegram) { $argLine += " -SkipTelegram" }
$desc = if ($SendTelegram) {
    "MKM lens daily auto: OOS promote, btrack 10lane, hardening, Telegram four_lens (B-track)."
} else {
    "MKM lens daily auto: OOS promote, btrack 10lane, hardening; Telegram four_lens OFF (08:28 prophecy only)."
}
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 45) -MultipleInstances IgnoreNew -Hidden
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
    -Description $desc -Force | Out-Null

$i = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "[DONE] $TaskName at $At Next=$($i.NextRunTime)" -ForegroundColor Green
