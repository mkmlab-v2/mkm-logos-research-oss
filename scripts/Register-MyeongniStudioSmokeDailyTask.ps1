#Requires -Version 5.1
<#
.SYNOPSIS
  Register daily Task Scheduler job for Myeongni research studio smoke chain (B-track).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-MyeongniStudioSmokeDailyTask.ps1 -At "08:50"

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-MyeongniStudioSmokeDailyTask.ps1 -Remove
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_MyeongniStudioSmoke_Daily",
    [string]$At = "08:50",
    [switch]$RunWhenLoggedOff,
    [switch]$Remove,
    [switch]$SkipHttp
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "projects\no1kmedi\scripts\run-myeongni-studio-smoke-chain.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing runner: $runner"
}

$log = Join-Path $WorkspaceRoot "reports\myeongni_studio_smoke_daily.log"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
    Write-Host "[DONE] Removed task (if existed): $TaskName" -ForegroundColor Yellow
    exit 0
}

$skipArg = if ($SkipHttp) { " -SkipHttp" } else { "" }
$cmdArgs = "/c cd /d `"$WorkspaceRoot`" && powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$runner`"$skipArg >> `"$log`" 2>&1"

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $cmdArgs
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

if ($RunWhenLoggedOff) {
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited
}

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Disable-ScheduledTask -TaskName $TaskName | Out-Null

Write-Host "[OK] Registered (Disabled): $TaskName daily at $At" -ForegroundColor Green
Write-Host "  Runner: $runner" -ForegroundColor DarkGray
Write-Host "  Log   : $log" -ForegroundColor DarkGray
Write-Host "  Enable: Enable-ScheduledTask -TaskName $TaskName (tier3 SSOT: MKM_MyeongniStudioSmoke_Daily)" -ForegroundColor DarkGray
