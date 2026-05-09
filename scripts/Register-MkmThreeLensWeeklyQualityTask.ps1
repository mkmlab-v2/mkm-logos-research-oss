<#
.SYNOPSIS
  Register/remove weekly task for MKM Three-Lens quality report.
#>
param(
  [switch]$Remove,
  [string]$TaskName = "MKM_ThreeLens_Weekly_Quality",
  [string]$WorkspaceRoot = "C:\workspace",
  [string]$At = "07:55",
  [ValidateSet("MON","TUE","WED","THU","FRI","SAT","SUN")]
  [string]$DayOfWeek = "SUN",
  [int]$WindowDays = 7
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $WorkspaceRoot "scripts\run_mkm_three_lens_weekly_quality_chain_v1.ps1"

if ($Remove) {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
  Write-Host "Removed scheduled task (if existed): $TaskName"
  exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
  throw "Runner not found: $runner"
}

$atTime = [DateTime]::ParseExact($At, "HH:mm", $null)
$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`" -WindowDays $WindowDays"

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek $DayOfWeek -At $atTime
$settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "Weekly Three-Lens quality report (GO/WATCH/HOLD distribution + safe-mode gate summary)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
  -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered: $TaskName (weekly $DayOfWeek at $At)"
Write-Host "Runner: $runner"
