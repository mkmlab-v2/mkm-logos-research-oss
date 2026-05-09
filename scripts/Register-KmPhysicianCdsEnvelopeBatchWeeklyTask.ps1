#Requires -Version 5.1
<#
.SYNOPSIS
  Register (or remove) weekly Scheduled Task: KM physician CDS envelope JSONL batch artifact refresh.

.DESCRIPTION
  Runs scripts/Run-KmPhysicianCdsEnvelopeBatchWeekly_v1.ps1 (demo fixture → reports/km_physician_cds_envelope_batch_latest.jsonl).
  Default: Sunday 09:45 local (after BTC hit-rate bundle default 09:15).

.PARAMETER Remove
  Unregister the task.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\Register-KmPhysicianCdsEnvelopeBatchWeeklyTask.ps1"

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\Register-KmPhysicianCdsEnvelopeBatchWeeklyTask.ps1" -SundayAt "10:00"

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\Register-KmPhysicianCdsEnvelopeBatchWeeklyTask.ps1" -Remove
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM-KmPhysician-CdsEnvelopeBatch-Weekly",
    [string]$SundayAt = "09:45",
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$AllowPartial,
    [switch]$DryRun,
    [switch]$RunWhenLoggedOff
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\Run-KmPhysicianCdsEnvelopeBatchWeekly_v1.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing runner script: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[DONE] Removed task (if existed): $TaskName" -ForegroundColor Yellow
    exit 0
}

$parts = $SundayAt -split ':'
if ($parts.Count -lt 2) {
    throw "SundayAt must be HH:mm (e.g. 09:45), got: $SundayAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`""
if ($AllowPartial) { $argLine += " -AllowPartial" }
if ($DryRun) { $argLine += " -DryRun" }

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -MultipleInstances IgnoreNew `
    -Hidden

$logonType = if ($RunWhenLoggedOff) { "S4U" } else { "Interactive" }
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType $logonType -RunLevel Limited
$desc = "Weekly CDS envelope JSONL batch → reports/km_physician_cds_envelope_batch_latest.jsonl (physician-assist schema; not diagnosis)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $desc -Force | Out-Null

$taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "[DONE] Registered task: $TaskName" -ForegroundColor Green
Write-Host "  NextRunTime : $($taskInfo.NextRunTime)"
Write-Host "  SundayAt    : $SundayAt"
Write-Host "  DryRun      : $DryRun"
Write-Host "  AllowPartial: $AllowPartial"
