param(
    [string]$Repo = "mkmlab-v2/mkm-destiny-ai-41e38ec6",
    [string]$RunnerName = "WIN-GPU-RUNNER-01",
    [switch]$CheckOnly,
    [int]$RecoveryPollSeconds = 30
)

$ErrorActionPreference = "Stop"
$LogPath = "C:\workspace\reports\github_gpu_runner_health_log.jsonl"

function Write-HealthLog {
    param(
        [int]$ExitCode,
        [string]$Message,
        [object]$BeforeState = $null,
        [object]$AfterState = $null,
        [string]$ServiceName = $null
    )
    $logDir = Split-Path -Parent $LogPath
    if (-not (Test-Path -LiteralPath $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    $entry = [ordered]@{
        ts_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        repo = $Repo
        runner = $RunnerName
        check_only = [bool]$CheckOnly.IsPresent
        recovery_poll_seconds = $RecoveryPollSeconds
        exit_code = $ExitCode
        message = $Message
        service_name = $ServiceName
        before = $BeforeState
        after = $AfterState
    }
    ($entry | ConvertTo-Json -Compress -Depth 6) | Add-Content -Path $LogPath -Encoding utf8
}

function Get-RunnerState {
    param(
        [string]$RepoName,
        [string]$TargetRunnerName
    )
    $json = gh api "repos/$RepoName/actions/runners"
    if ([string]::IsNullOrWhiteSpace($json)) {
        return $null
    }
    $doc = $json | ConvertFrom-Json
    if ($null -eq $doc -or $null -eq $doc.runners) {
        return $null
    }
    $runner = @($doc.runners | Where-Object { $_.name -eq $TargetRunnerName } | Select-Object -First 1)
    if ($runner.Count -eq 0) {
        return $null
    }
    return [PSCustomObject]@{
        name = $runner[0].name
        status = $runner[0].status
        busy = $runner[0].busy
        labels = @($runner[0].labels | ForEach-Object { $_.name })
    }
}

function Find-RunnerService {
    param(
        [string]$TargetRunnerName
    )
    $services = @(Get-Service "actions.runner*" -ErrorAction SilentlyContinue)
    if ($services.Count -eq 0) {
        return $null
    }
    $match = $services | Where-Object { $_.Name -like "*$TargetRunnerName*" } | Select-Object -First 1
    if ($null -ne $match) {
        return $match
    }
    return ($services | Select-Object -First 1)
}

$before = Get-RunnerState -RepoName $Repo -TargetRunnerName $RunnerName
if ($null -eq $before) {
    $msg = "Runner not found: $RunnerName (repo=$Repo)"
    Write-Host $msg
    Write-HealthLog -ExitCode 2 -Message $msg -BeforeState $null
    exit 2
}

Write-Host "Runner status before: name=$($before.name) status=$($before.status) busy=$($before.busy)"

if ($before.status -eq "online") {
    $msg = "Runner is already online. No action needed."
    Write-Host $msg
    Write-HealthLog -ExitCode 0 -Message $msg -BeforeState $before -AfterState $before
    exit 0
}

if ($CheckOnly.IsPresent) {
    $msg = "CheckOnly mode: runner is offline; restart skipped."
    Write-Host $msg
    Write-HealthLog -ExitCode 1 -Message $msg -BeforeState $before
    exit 1
}

$svc = Find-RunnerService -TargetRunnerName $RunnerName
if ($null -eq $svc) {
    $msg = "No actions.runner* service found. Start runner manually with .\\run.cmd in runner directory."
    Write-Host $msg
    Write-HealthLog -ExitCode 3 -Message $msg -BeforeState $before
    exit 3
}

Write-Host "Attempting service restart: $($svc.Name)"
try {
    Restart-Service -Name $svc.Name -ErrorAction Stop
}
catch {
    $msg = "Restart-Service failed: $($_.Exception.Message)"
    Write-Host $msg
    Write-HealthLog -ExitCode 4 -Message $msg -BeforeState $before -ServiceName $svc.Name
    exit 4
}

Start-Sleep -Seconds $RecoveryPollSeconds
$after = Get-RunnerState -RepoName $Repo -TargetRunnerName $RunnerName
if ($null -eq $after) {
    $msg = "Runner disappeared after restart attempt: $RunnerName"
    Write-Host $msg
    Write-HealthLog -ExitCode 5 -Message $msg -BeforeState $before -ServiceName $svc.Name
    exit 5
}

Write-Host "Runner status after: name=$($after.name) status=$($after.status) busy=$($after.busy)"
if ($after.status -ne "online") {
    $msg = "Runner is still offline after restart."
    Write-Host $msg
    Write-HealthLog -ExitCode 6 -Message $msg -BeforeState $before -AfterState $after -ServiceName $svc.Name
    exit 6
}

Write-Host "Runner recovery successful."
Write-HealthLog -ExitCode 0 -Message "Runner recovery successful." -BeforeState $before -AfterState $after -ServiceName $svc.Name
exit 0
