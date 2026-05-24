#Requires -Version 5.1
<#
.SYNOPSIS
  Weekly Prophecy Sandbox Phase3 refresh (Binance fetch + join + full sandbox chain).

.NOTES
  research_only — does not mutate prod btrack_prophecy_score_latest.json body.
  Default: Saturday 08:45 local (before daily 08:50 if both enabled).
  Weekly chain passes --strict-health (watchlist gate: max_n_calendar_days>=3).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$At = "08:45",
    [ValidateSet("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")]
    [string]$DayOfWeek = "Saturday",
    [string]$TaskName = "MKM-Prophecy-Sandbox-WeeklyPhase3",
    [switch]$Unregister,
    [switch]$DryRun,
    [switch]$SkipMarketFetch,
    [switch]$RunWhenLoggedOff
)

$ErrorActionPreference = "Stop"
$script = Join-Path $WorkspaceRoot "scripts\run_prophecy_sandbox_weekly_phase3_v1.py"
$argParts = @("`"$script`"")
if ($SkipMarketFetch) {
    $argParts += "--skip-market-fetch"
}
$argStr = $argParts -join " "

if ($DryRun) {
    Write-Host "TaskName=$TaskName Day=$DayOfWeek At=$At Args=$argStr"
    exit 0
}

if ($Unregister) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Unregistered $TaskName"
    exit 0
}

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DayOfWeek -At $At
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 3) -MultipleInstances IgnoreNew -Hidden
$logonType = if ($RunWhenLoggedOff) { "S4U" } else { "Interactive" }
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType $logonType -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action (
    New-ScheduledTaskAction -Execute "py.exe" -Argument $argStr -WorkingDirectory $WorkspaceRoot
) -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Write-Host "Registered $TaskName weekly on $DayOfWeek at $At (LogonType=$logonType)"
Write-Host "Args: $argStr"
