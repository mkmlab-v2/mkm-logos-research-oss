<#
.SYNOPSIS
  Register (or remove) a weekly Scheduled Task for full free local CI bundle.

.DESCRIPTION
  Runs scripts/run_free_local_ci_bundle.ps1 with full options
  (includes Fact-Lock and no1kmedi build) once a week.

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Scheduled task name (default: MKM_FreeLocalCI_WeeklyFull).

.PARAMETER SundayAt
  Local time HH:mm for weekly Sunday trigger (default: 08:10).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_FreeLocalCI_WeeklyFull",
    [string]$SundayAt = "08:10"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_free_local_ci_bundle.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $SundayAt -split ':'
if ($parts.Count -lt 2) {
    throw "SundayAt must be HH:mm (e.g. 08:10), got: $SundayAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -RunNo1kmediBuild"

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $argLine `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 6)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "Weekly full free local CI: Fact-Lock + manseryeok + L1 smoke + no1kmedi build."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (weekly Sunday $SundayAt local, user=$env:USERNAME)"
Write-Host "Runner: $runner"
Write-Host "Args : $argLine"
