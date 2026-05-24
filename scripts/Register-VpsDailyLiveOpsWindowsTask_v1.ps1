#Requires -Version 5.1
<#
.SYNOPSIS
  Register daily Windows task: Run-VpsDailyLiveOpsBundle_v1.ps1 (ensemble v2 + VPS sync).

.EXAMPLE
  powershell -File scripts\Register-VpsDailyLiveOpsWindowsTask_v1.ps1 -DailyAt 07:05
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM-VpsDailyLiveOps-Bundle",
    [string]$DailyAt = "07:05",
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$RunWhenLoggedOff
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $WorkspaceRoot "scripts\Run-VpsDailyLiveOpsBundle_v1.ps1"
if (-not (Test-Path -LiteralPath $runner)) { throw "Missing $runner" }

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[DONE] Removed task: $TaskName" -ForegroundColor Yellow
    exit 0
}

$parts = $DailyAt -split ':'
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$atToday = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -SkipCronRegister"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $atToday
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew `
    -Hidden

$logonType = if ($RunWhenLoggedOff) { "S4U" } else { "Interactive" }
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType $logonType -RunLevel Limited
$desc = "Daily: ensemble v2 risk refresh, VPS export, GO/risk sync (B-track [HYPO]; not auto order logic)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $desc -Force | Out-Null
$info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "[DONE] Registered: $TaskName NextRun=$($info.NextRunTime) At=$DailyAt" -ForegroundColor Green
