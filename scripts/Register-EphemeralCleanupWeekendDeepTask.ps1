<#
.SYNOPSIS
  Register (or remove) a weekly weekend deep-clean task for ephemeral files.
  This profile includes tmp cleanup.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "Workspace_EphemeralCleanup_WeekendDeep",
    [string]$WeeklyAt = "05:10",
    [ValidateSet("Sunday", "Saturday")]
    [string]$DayOfWeek = "Sunday",
    [int]$RetentionDays = 7,
    [int]$MaxDeleteCount = 0
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Invoke-EphemeralCleanup.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $WeeklyAt -split ':'
if ($parts.Count -lt 2) {
    throw "WeeklyAt must be HH:mm (e.g. 05:10), got: $WeeklyAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$base = Get-Date
$atToday = Get-Date -Year $base.Year -Month $base.Month -Day $base.Day -Hour $hour -Minute $minute -Second 0

$arg = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -RetentionDays $RetentionDays -IncludeTmp"
if ($MaxDeleteCount -gt 0) {
    $arg += " -MaxDeleteCount $MaxDeleteCount"
}
$arg += " -Apply"

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg -WorkingDirectory $workspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DayOfWeek -At $atToday
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "Weekly deep cleanup for ephemeral files including tmp paths."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName ($DayOfWeek at $WeeklyAt, retention=$RetentionDays days, include_tmp=true)"
Write-Host "Runner: $runner"
