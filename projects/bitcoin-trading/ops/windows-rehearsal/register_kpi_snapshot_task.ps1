$ErrorActionPreference = "Stop"

$taskName = "Bitcoin-KPI-Snapshot-30min"
$projectRoot = "C:\workspace\projects\bitcoin-trading"
$runner = Join-Path $projectRoot "ops\windows-rehearsal\run_kpi_snapshot.ps1"

if (-not (Test-Path $runner)) {
    throw "KPI runner wrapper not found: $runner"
}

$tr = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$runner`""

schtasks /Delete /TN $taskName /F | Out-Null 2>&1
schtasks /Create /TN $taskName /SC MINUTE /MO 30 /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create KPI task. ExitCode=$LASTEXITCODE"
}

Write-Host "Created scheduled task: $taskName"
Write-Host "Command: $tr"
