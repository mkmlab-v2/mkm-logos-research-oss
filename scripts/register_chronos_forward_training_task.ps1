<#
.SYNOPSIS
  Register (or remove) weekly Chronos-Forward baseline training task.

.DESCRIPTION
  Schedules:
    C:\workspace\scripts\run_chronos_forward_kospi_baseline.ps1 -Mode both -Compute gpu -Quiet

  This is research/training automation only (no live trading).

.PARAMETER Remove
  If set, unregister task.

.PARAMETER TaskName
  Scheduled task name.

.PARAMETER WeeklyOn
  Day of week (MON..SUN).

.PARAMETER At
  Time HH:mm (24h).

.PARAMETER Mode
  training | holdout2026 | both

.PARAMETER Quiet
  If set, passes -Quiet to runner.
#>

param(
  [switch]$Remove,
  [string]$TaskName = "Chronos-Forward Weekly Training",
  [ValidateSet("MON","TUE","WED","THU","FRI","SAT","SUN")]
  [string]$WeeklyOn = "SUN",
  [string]$At = "03:30",
  [ValidateSet("training","holdout2026","both")]
  [string]$Mode = "both",
  [switch]$Quiet
)

$ErrorActionPreference = "Stop"

$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_chronos_forward_kospi_baseline.ps1"

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

$args = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -Mode $Mode -Compute gpu"
if ($Quiet) {
  $args += " -Quiet"
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $args
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $daysOfWeek -At $At
$settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries

# Keep behavior aligned with existing local task registrations.
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Principal $principal `
  -Description "Weekly Chronos-Forward training baseline (Mode=$Mode)" `
  -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName"
Write-Host "WeeklyOn: $WeeklyOn ($daysOfWeek) At: $At"
Write-Host "Mode: $Mode Quiet: $($Quiet.IsPresent)"
Write-Host "Runner: $runner"

