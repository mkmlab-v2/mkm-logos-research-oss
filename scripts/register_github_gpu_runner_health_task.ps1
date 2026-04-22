param(
    [switch]$Remove,
    [string]$TaskName = "MKM_GitHubGpuRunner_Healthcheck",
    [int]$EveryMinutes = 5,
    [string]$Repo = "mkmlab-v2/mkm-destiny-ai-41e38ec6",
    [string]$RunnerName = "WIN-GPU-RUNNER-01"
)

$ErrorActionPreference = "Stop"

$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\check_github_gpu_runner_health.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}
if ($EveryMinutes -lt 1) {
    throw "EveryMinutes must be >= 1"
}

$startTime = (Get-Date).AddMinutes(1).ToString("HH:mm")
$taskRun = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -Repo `"$Repo`" -RunnerName `"$RunnerName`""

schtasks /Create `
    /TN $TaskName `
    /TR $taskRun `
    /SC MINUTE `
    /MO $EveryMinutes `
    /ST $startTime `
    /F | Out-Null

Write-Host "Registered scheduled task: $TaskName"
Write-Host "Runner script: $runner"
Write-Host "Target runner: $RunnerName"
Write-Host "Repo: $Repo"
Write-Host "Interval: every ${EveryMinutes} minutes"
