<#
.SYNOPSIS
  Register or remove a weekly scheduled task for XAI contract reporting.

.DESCRIPTION
  Runs scripts/run_xai_contract_weekly_reporting_v1.ps1 once per week.
#>
param(
  [switch]$Remove,
  [string]$TaskName = "MKM_XAI_Contract_Weekly_Reporting",
  [string]$WorkspaceRoot = "C:\workspace",
  [string]$At = "07:45",
  [ValidateSet("MON","TUE","WED","THU","FRI","SAT","SUN")]
  [string]$DayOfWeek = "SUN",
  [int]$WindowDays = 7,
  [string]$DefaultOwner = "xai-ops",
  [int]$DueDays = 2
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $WorkspaceRoot "scripts\run_xai_contract_weekly_reporting_v1.ps1"

if ($Remove) {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
  Write-Host "Removed scheduled task (if existed): $TaskName"
  exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
  throw "Runner not found: $runner"
}

$atTime = [DateTime]::ParseExact($At, "HH:mm", $null)
$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`" -WindowDays $WindowDays -DefaultOwner `"$DefaultOwner`" -DueDays $DueDays"

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek $DayOfWeek -At $atTime
$settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "Weekly XAI contract reporting (weekly metrics + ops action queue)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
  -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered: $TaskName (weekly $DayOfWeek at $At)"
Write-Host "Runner: $runner"
