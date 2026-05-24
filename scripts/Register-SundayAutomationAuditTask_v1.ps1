#Requires -Version 5.1
<#
.SYNOPSIS
  Register weekly Sunday post-flight audit (after V2 Wire 10:15 chain).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-SundayAutomationAuditTask_v1.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-SundayAutomationAuditTask_v1.ps1 -Remove
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM-Sunday-Automation-LastResult-Audit",
    [string]$SundayAt = "10:30",
    [switch]$RunWhenLoggedOff,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\Invoke-CheckSundayAutomationLastResult_v1.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing audit script: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[DONE] Removed task (if existed): $TaskName" -ForegroundColor Yellow
    exit 0
}

$outJson = Join-Path $WorkspaceRoot "reports\sunday_automation_audit_latest.json"
$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`" -OutJson `"$outJson`" -AlsoVerifyHeadlineLane"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot

$parts = $SundayAt -split ':'
if ($parts.Count -lt 2) { throw "SundayAt must be HH:mm (e.g. 10:30)" }
$at = Get-Date -Hour ([int]$parts[0]) -Minute ([int]$parts[1]) -Second 0

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 15) -MultipleInstances IgnoreNew -Hidden
$logonType = if ($RunWhenLoggedOff) { "S4U" } else { "Interactive" }
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType $logonType -RunLevel Limited
$desc = "Weekly Sunday: LastTaskResult audit for B-track/panel/sweep/V2 wire; optional headline lane pointer check."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $desc -Force | Out-Null

$taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "[DONE] Registered task: $TaskName" -ForegroundColor Green
Write-Host "  NextRunTime   : $($taskInfo.NextRunTime)"
Write-Host "  LastTaskResult: $($taskInfo.LastTaskResult)"
Write-Host "  SundayAt      : $SundayAt (local)"
Write-Host "  LogonType     : $logonType"
