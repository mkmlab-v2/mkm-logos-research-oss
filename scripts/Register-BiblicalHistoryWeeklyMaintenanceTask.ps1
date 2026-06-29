<#
.SYNOPSIS
  Register (or remove) weekly scheduled task for B-track biblical history maintenance.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_BiblicalHistory_WeeklyMaintenance",
    [ValidateSet("MON","TUE","WED","THU","FRI","SAT","SUN")]
    [string]$WeeklyDay = "SUN",
    [string]$WeeklyAt = "09:15",
    [int]$LookbackDays = 90
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_biblical_history_weekly_maintenance_v1.py"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $WeeklyAt -split ':'
if ($parts.Count -lt 2) { throw "WeeklyAt must be HH:mm, got: $WeeklyAt" }

$argLine = "`"$runner`" --lookback-days $LookbackDays"
$action = New-ScheduledTaskAction -Execute "py" -Argument $argLine -WorkingDirectory $workspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek $WeeklyDay -At $WeeklyAt
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Weekly B-track biblical history maintenance (reconciliation, slice, AB, pytest). research_only."
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (weekly $WeeklyDay $WeeklyAt, user=$env:USERNAME)"
Write-Host "Runner: py $runner --lookback-days $LookbackDays"
