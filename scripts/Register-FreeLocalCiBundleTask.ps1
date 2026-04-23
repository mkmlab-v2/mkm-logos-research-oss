<#
.SYNOPSIS
  Register (or remove) a daily Scheduled Task for free local CI bundle.

.DESCRIPTION
  Runs scripts/run_free_local_ci_bundle.ps1 on a daily schedule so core checks
  continue without GitHub-hosted runners.

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Scheduled task name (default: MKM_FreeLocalCI_Daily).

.PARAMETER DailyAt
  Local time HH:mm (default: 07:20).

.PARAMETER IncludeFactLock
  Include heavy Fact-Lock bundle in scheduled run.

.PARAMETER IncludeNo1kmediBuild
  Include no1kmedi npm build in scheduled run.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_FreeLocalCI_Daily",
    [string]$DailyAt = "07:20",
    [switch]$IncludeFactLock,
    [switch]$IncludeNo1kmediBuild
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

$parts = $DailyAt -split ':'
if ($parts.Count -lt 2) {
    throw "DailyAt must be HH:mm (e.g. 07:20), got: $DailyAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`""
if (-not $IncludeFactLock) {
    $argLine += " -SkipFactLock"
}
if (-not $IncludeNo1kmediBuild) {
    $argLine += " -SkipNo1kmediBuild"
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $argLine `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Daily -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Daily free local CI: manseryeok + L1 smoke (+ optional Fact-Lock/no1kmedi build)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (daily $DailyAt local, user=$env:USERNAME)"
Write-Host "Runner: $runner"
Write-Host "Args : $argLine"
