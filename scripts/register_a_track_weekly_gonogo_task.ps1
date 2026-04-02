<# 
.SYNOPSIS
  Register (or remove) Windows Scheduled Task for weekly A-Track Go/No-Go.

.DESCRIPTION
  Creates a weekly task that runs:
    C:\workspace\scripts\run_a_track_weekly_check.ps1 -OnSystemError no_go

.PARAMETER Remove
  If set, unregister the task.

.PARAMETER TaskName
  Scheduled Task name.

.PARAMETER WeeklyOn
  Day of week.

.PARAMETER At
  Time in HH:mm (24h).
#>

param(
  [switch]$Remove,
  [string]$TaskName = "A-Track Weekly GoNoGo",
  [ValidateSet("MON","TUE","WED","THU","FRI","SAT","SUN")]
  [string]$WeeklyOn = "MON",
  [string]$At = "09:30"
)

$ErrorActionPreference = "Stop"

$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_a_track_weekly_check.ps1"

if ($Remove) {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
  Write-Host "Removed scheduled task: $TaskName"
  exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
  throw "Runner not found: $runner"
}

$parts = $At -split ':'
if ($parts.Count -lt 2) {
  throw "At must be HH:mm, got: $At"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
if ($hour -lt 0 -or $hour -gt 23 -or $minute -lt 0 -or $minute -gt 59) {
  throw "At out of range (HH:mm): $At"
}

$dayMap = @{
  "MON" = "Monday"
  "TUE" = "Tuesday"
  "WED" = "Wednesday"
  "THU" = "Thursday"
  "FRI" = "Friday"
  "SAT" = "Saturday"
  "SUN" = "Sunday"
}
$daysOfWeek = $dayMap[$WeeklyOn]

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runner`" -OnSystemError no_go"

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $daysOfWeek -At $At

$settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

# Interactive login so user context + .env reads behave like local runs.
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Principal $principal `
  -Description "Weekly A-Track Go/No-Go (Slack webhook + fail-safe NO_GO)" `
  -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName"
Write-Host "WeeklyOn: $WeeklyOn ($daysOfWeek) At: $At"
Write-Host "Runner: $runner"

