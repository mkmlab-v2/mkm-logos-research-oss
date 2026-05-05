<#
.SYNOPSIS
  Register or remove a 24h long-running memory-ops scheduled task.

.DESCRIPTION
  Runs Invoke-LongRunMemoryOpsCycle.ps1 repeatedly for a bounded duration
  (default: every 30 minutes for 24 hours), focused on safe health/ops checks.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_LongRunMemoryOps_24h",
    [int]$RepeatMinutes = 30,
    [int]$DurationHours = 24,
    [switch]$SkipNewsObservationContractSmoke,
    [switch]$SkipSecretExposureSurvey
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Invoke-LongRunMemoryOpsCycle.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}
if ($RepeatMinutes -lt 5) {
    throw "RepeatMinutes must be >= 5"
}
if ($DurationHours -lt 1) {
    throw "DurationHours must be >= 1"
}

$startAt = (Get-Date).AddMinutes(1)
$startTimeText = $startAt.ToString("HH:mm")
$runnerArgs = @(
    "-NoProfile",
    "-WindowStyle", "Hidden",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$runner`""
)
if ($SkipNewsObservationContractSmoke) {
    $runnerArgs += "-SkipNewsObservationContractSmoke"
}
if ($SkipSecretExposureSurvey) {
    $runnerArgs += "-SkipSecretExposureSurvey"
}
$argLine = $runnerArgs -join " "

$taskCmd = "powershell.exe $argLine"

$createArgs = @(
    "/Create",
    "/F",
    "/TN", $TaskName,
    "/SC", "MINUTE",
    "/MO", "$RepeatMinutes",
    "/DU", ("{0:00}:00" -f $DurationHours),
    "/ST", $startTimeText,
    "/TR", $taskCmd
)

& schtasks @createArgs | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to register scheduled task via schtasks.exe (exit $LASTEXITCODE)"
}

Write-Host "Registered scheduled task: $TaskName"
Write-Host "StartAt: $startAt"
Write-Host "Repeat: every $RepeatMinutes minute(s), duration ${DurationHours}h"
Write-Host "Runner: $runner"
Write-Host "Argument: $argLine"

