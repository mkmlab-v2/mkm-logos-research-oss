param(
    [switch]$Remove,
    [string]$TaskName = "MKM_GitHubGpuRunner_AlertReplay",
    [int]$EveryMinutes = 3
)

$ErrorActionPreference = "Stop"

$scriptPath = "C:\workspace\scripts\replay_gpu_runner_health_alert_queue.ps1"
if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Replay script not found: $scriptPath"
}
if ($EveryMinutes -lt 1) {
    throw "EveryMinutes must be >= 1"
}

$startTime = (Get-Date).AddMinutes(1).ToString("HH:mm")
$taskRun = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`""

& schtasks /Create /TN $TaskName /TR $taskRun /SC MINUTE /MO $EveryMinutes /ST $startTime /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to register scheduled task (exit_code=$LASTEXITCODE)."
}

Write-Host "Registered scheduled task: $TaskName"
Write-Host "Replay script: $scriptPath"
Write-Host "Interval: every ${EveryMinutes} minutes"
