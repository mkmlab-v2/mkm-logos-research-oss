param(
    [switch]$Remove,
    [string]$TaskName = "MKM_GitHubGpuRunner_Healthcheck",
    [int]$EveryMinutes = 5,
    [string]$Repo = "mkmlab-v2/mkm-destiny-ai-41e38ec6",
    [string]$RunnerName = "WIN-GPU-RUNNER-01",
    [int]$RecoveryPollSeconds = 30,
    [int]$MaxRecoveryAttempts = 3,
    [switch]$RunWithHighestPrivileges
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
if ($RecoveryPollSeconds -lt 5) {
    throw "RecoveryPollSeconds must be >= 5"
}
if ($MaxRecoveryAttempts -lt 1) {
    throw "MaxRecoveryAttempts must be >= 1"
}

$startTime = (Get-Date).AddMinutes(1).ToString("HH:mm")
$taskRun = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -Repo `"$Repo`" -RunnerName `"$RunnerName`" -RecoveryPollSeconds $RecoveryPollSeconds -MaxRecoveryAttempts $MaxRecoveryAttempts"

$createArgs = @(
    "/Create"
    "/TN", $TaskName
    "/TR", $taskRun
    "/SC", "MINUTE"
    "/MO", "$EveryMinutes"
    "/ST", $startTime
    "/F"
)
if ($RunWithHighestPrivileges.IsPresent) {
    $createArgs += @("/RL", "HIGHEST")
}

& schtasks @createArgs | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to register scheduled task (exit_code=$LASTEXITCODE)."
}

Write-Host "Registered scheduled task: $TaskName"
Write-Host "Runner script: $runner"
Write-Host "Target runner: $RunnerName"
Write-Host "Repo: $Repo"
Write-Host "Interval: every ${EveryMinutes} minutes"
Write-Host "Recovery poll seconds: $RecoveryPollSeconds"
Write-Host "Max recovery attempts: $MaxRecoveryAttempts"
Write-Host "Run with highest privileges: $($RunWithHighestPrivileges.IsPresent)"
