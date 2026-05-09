<#
.SYNOPSIS
  Register (or remove) weekly IP fortress scrubber (public-facing text sweep).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_IpFortress_Scrubber_Weekly",
    [ValidateSet("Sunday", "Saturday")]
    [string]$DayOfWeek = "Sunday",
    [string]$WeeklyAt = "04:30"
)

$ErrorActionPreference = "Stop"

$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\background_jobs\ip_fortress_scrubber_v1.py"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $WeeklyAt -split ":"
if ($parts.Count -lt 2) {
    throw "WeeklyAt must be HH:mm. Got: $WeeklyAt"
}

$hour = [int]$parts[0]
$minute = [int]$parts[1]
$base = Get-Date
$atToday = Get-Date -Year $base.Year -Month $base.Month -Day $base.Day -Hour $hour -Minute $minute -Second 0

$arg = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command `"py '$runner'`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg -WorkingDirectory $workspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DayOfWeek -At $atToday
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "Weekly scan for IP-sensitive tokens in allowlisted public surfaces (Fact-Lock artifact)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName ($DayOfWeek at $WeeklyAt)"
Write-Host "Runner: $runner"
