param(
    [string]$Repo = "mkmlab-v2/mkm-destiny-ai-41e38ec6",
    [string]$RunnerName = "WIN-GPU-RUNNER-01",
    [switch]$CheckOnly,
    [int]$RecoveryPollSeconds = 30
)

$ErrorActionPreference = "Stop"

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
    Write-Host "Runner not found: $RunnerName (repo=$Repo)"
    exit 2
}

Write-Host "Runner status before: name=$($before.name) status=$($before.status) busy=$($before.busy)"

if ($before.status -eq "online") {
    Write-Host "Runner is already online. No action needed."
    exit 0
}

if ($CheckOnly.IsPresent) {
    Write-Host "CheckOnly mode: runner is offline; restart skipped."
    exit 1
}

$svc = Find-RunnerService -TargetRunnerName $RunnerName
if ($null -eq $svc) {
    Write-Host "No actions.runner* service found. Start runner manually with .\\run.cmd in runner directory."
    exit 3
}

Write-Host "Attempting service restart: $($svc.Name)"
try {
    Restart-Service -Name $svc.Name -ErrorAction Stop
}
catch {
    Write-Host "Restart-Service failed: $($_.Exception.Message)"
    exit 4
}

Start-Sleep -Seconds $RecoveryPollSeconds
$after = Get-RunnerState -RepoName $Repo -TargetRunnerName $RunnerName
if ($null -eq $after) {
    Write-Host "Runner disappeared after restart attempt: $RunnerName"
    exit 5
}

Write-Host "Runner status after: name=$($after.name) status=$($after.status) busy=$($after.busy)"
if ($after.status -ne "online") {
    Write-Host "Runner is still offline after restart."
    exit 6
}

Write-Host "Runner recovery successful."
exit 0
