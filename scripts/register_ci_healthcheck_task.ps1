param(
    [switch]$Remove,
    [string]$TaskName = "MKM_CI_Healthcheck_Cycle",
    [int]$EveryMinutes = 60
)

$ErrorActionPreference = "Stop"

$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_ci_healthcheck_cycle.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}
if ($EveryMinutes -lt 10) {
    throw "EveryMinutes must be >= 10"
}

$startTime = (Get-Date).AddMinutes(1).ToString("HH:mm")
$taskRun = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$runner`""

schtasks /Create `
    /TN $TaskName `
    /TR $taskRun `
    /SC MINUTE `
    /MO $EveryMinutes `
    /ST $startTime `
    /F | Out-Null

Write-Host "Registered scheduled task: $TaskName"
Write-Host "Runner: $runner"
Write-Host "Interval: every ${EveryMinutes} minutes"
