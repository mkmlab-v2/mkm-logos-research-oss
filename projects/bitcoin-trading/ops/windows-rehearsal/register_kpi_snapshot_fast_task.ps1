param(
    [int]$IntervalMinutes = 5
)

$taskName = "Bitcoin-KPI-Snapshot-5min"
$projectRoot = "C:\workspace\projects\bitcoin-trading"
$runner = Join-Path $projectRoot "ops\windows-rehearsal\run_kpi_snapshot.ps1"

if (-not (Test-Path $runner)) {
    throw "Runner not found: $runner"
}

$tr = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$runner`""

schtasks /Delete /TN $taskName /F | Out-Null 2>&1
schtasks /Create /TN $taskName /SC MINUTE /MO $IntervalMinutes /TR $tr /F | Out-Null

Write-Host "Registered task: $taskName (every $IntervalMinutes min)"
