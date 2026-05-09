[CmdletBinding()]
param(
    [switch]$Remove,
    [switch]$StartNow,
    [string]$TaskName = "MKM-Execution-Gate-Audit-Summary-15min",
    [int]$IntervalMinutes = 15
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$runner = Join-Path $PSScriptRoot "Run-ExecutionGateAuditSummaryTask.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "scheduled_task: REMOVED ($TaskName)"
    exit 0
}

$interval = [Math]::Max(1, $IntervalMinutes)
$runCmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$runner`""

schtasks /Create /TN $TaskName /TR $runCmd /SC MINUTE /MO $interval /RL LIMITED /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to register task: $TaskName (exit=$LASTEXITCODE)"
}

Write-Output "scheduled_task: REGISTERED ($TaskName)"
Write-Output "interval_minutes=$interval"

if ($StartNow) {
    Start-ScheduledTask -TaskName $TaskName
    Write-Output "scheduled_task: STARTED ($TaskName)"
}
