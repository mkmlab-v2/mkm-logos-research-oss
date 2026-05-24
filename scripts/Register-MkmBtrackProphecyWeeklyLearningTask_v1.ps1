#Requires -Version 5.1
<#
.SYNOPSIS
  Register weekly B-track prophecy learning task (after auto-sweep slot).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-MkmBtrackProphecyWeeklyLearningTask_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM-BTrack-Prophecy-Weekly-Learning",
    [string]$SundayAt = "10:15",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $WorkspaceRoot "scripts\Invoke-MkmBtrackProphecyWeeklyLearning_v1.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[DONE] Removed: $TaskName" -ForegroundColor Yellow
    exit 0
}

$parts = $SundayAt -split ':'
$at = Get-Date -Hour ([int]$parts[0]) -Minute ([int]$parts[1]) -Second 0
$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`" -SkipAutoSweep"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 4) -MultipleInstances IgnoreNew -Hidden
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
    -Description "Weekly B-track: promote sweep to artifacts + 30d eval + WF + watchdog ([HYPO])." -Force | Out-Null
$info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "[DONE] $TaskName at $SundayAt (LogonType=Interactive) Next=$($info.NextRunTime)" -ForegroundColor Green
