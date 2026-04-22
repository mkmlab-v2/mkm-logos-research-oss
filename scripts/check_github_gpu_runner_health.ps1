param(
    [string]$Repo = "mkmlab-v2/mkm-destiny-ai-41e38ec6",
    [string]$RunnerName = "WIN-GPU-RUNNER-01",
    [switch]$CheckOnly,
    [int]$RecoveryPollSeconds = 30,
    [int]$MaxRecoveryAttempts = 3,
    [string]$WebhookUrl = "",
    [string]$RunnerDir = "C:\workspace\actions-runner-gpu"
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

function Send-HealthAlert {
    param(
        [int]$ExitCode,
        [string]$Message,
        [object]$BeforeState = $null,
        [object]$AfterState = $null,
        [string]$ServiceName = $null
    )
    $url = $WebhookUrl
    if ([string]::IsNullOrWhiteSpace($url)) {
        $url = $env:RUNNER_HEALTH_WEBHOOK_URL
    }
    if ([string]::IsNullOrWhiteSpace($url)) {
        $url = $env:OPS_ALARM_WEBHOOK_URL
    }
    if ([string]::IsNullOrWhiteSpace($url)) {
        return
    }
    $beforeStatus = if ($null -ne $BeforeState) { $BeforeState.status } else { "unknown" }
    $afterStatus = if ($null -ne $AfterState) { $AfterState.status } else { "unknown" }
    $hostName = $env:COMPUTERNAME
    $severity = if ($ExitCode -ge 4) { "critical" } else { "warning" }
    $summaryText = "[$severity] runner=$RunnerName exit_code=$ExitCode before=$beforeStatus after=$afterStatus message=$Message"
    $payload = @{
        event = "github_gpu_runner_health_alert"
        kind = "failure"
        severity = $severity
        title = "GitHub GPU runner health alert"
        message = $summaryText
        text = $summaryText
        ts_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        host = $hostName
        repo = $Repo
        runner = $RunnerName
        check_only = [bool]$CheckOnly.IsPresent
        recovery_poll_seconds = $RecoveryPollSeconds
        max_recovery_attempts = $MaxRecoveryAttempts
        exit_code = $ExitCode
        service_name = $ServiceName
        before = $BeforeState
        after = $AfterState
        fields = @{
            host = $hostName
            repo = $Repo
            runner = $RunnerName
            check_only = [bool]$CheckOnly.IsPresent
            recovery_poll_seconds = $RecoveryPollSeconds
            max_recovery_attempts = $MaxRecoveryAttempts
            service_name = $ServiceName
            before_status = $beforeStatus
            after_status = $afterStatus
            exit_code = $ExitCode
        }
        blocks = @(
            @{
                type = "header"
                text = @{
                    type = "plain_text"
                    text = "GitHub GPU runner health alert"
                }
            },
            @{
                type = "section"
                text = @{
                    type = "mrkdwn"
                    text = "*Severity:* $severity`n*Runner:* $RunnerName`n*Repo:* $Repo`n*Message:* $Message"
                }
            },
            @{
                type = "section"
                fields = @(
                    @{ type = "mrkdwn"; text = "*Before:*\n$beforeStatus" },
                    @{ type = "mrkdwn"; text = "*After:*\n$afterStatus" },
                    @{ type = "mrkdwn"; text = "*Exit code:*\n$ExitCode" },
                    @{ type = "mrkdwn"; text = "*Host:*\n$hostName" }
                )
            }
        )
    } | ConvertTo-Json -Depth 6
    try {
        Invoke-RestMethod -Uri $url -Method Post -ContentType "application/json; charset=utf-8" -Body $payload | Out-Null
    }
    catch {
        Write-Host "WARN: webhook send failed: $($_.Exception.Message)"
    }
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

function Start-RunnerProcess {
    param(
        [string]$WorkingDirectory
    )
    $runCmd = Join-Path $WorkingDirectory "run.cmd"
    if (-not (Test-Path -LiteralPath $runCmd)) {
        throw "run.cmd not found: $runCmd"
    }
    # Avoid duplicate interactive runner processes.
    $alreadyRunning = @(Get-CimInstance Win32_Process -Filter "Name = 'cmd.exe'" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*actions-runner-gpu*run.cmd*"
    })
    if ($alreadyRunning.Count -gt 0) {
        return
    }
    Start-Process -FilePath $runCmd -WorkingDirectory $WorkingDirectory | Out-Null
}

function Wait-RunnerOnline {
    param(
        [string]$RepoName,
        [string]$TargetRunnerName,
        [int]$PollSeconds
    )
    Start-Sleep -Seconds $PollSeconds
    return Get-RunnerState -RepoName $RepoName -TargetRunnerName $TargetRunnerName
}

$before = Get-RunnerState -RepoName $Repo -TargetRunnerName $RunnerName
if ($null -eq $before) {
    $msg = "Runner not found: $RunnerName (repo=$Repo)"
    Write-Host $msg
    Send-HealthAlert -ExitCode 2 -Message $msg
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
    Send-HealthAlert -ExitCode 1 -Message $msg -BeforeState $before
    Write-HealthLog -ExitCode 1 -Message $msg -BeforeState $before
    exit 1
}

$svc = Find-RunnerService -TargetRunnerName $RunnerName
if ($null -eq $svc) {
    Write-Host "No actions.runner* service found. Attempting process-based recovery via run.cmd (max_attempts=$MaxRecoveryAttempts)."
    for ($attempt = 1; $attempt -le $MaxRecoveryAttempts; $attempt++) {
        try {
            Start-RunnerProcess -WorkingDirectory $RunnerDir
        }
        catch {
            $msg = "Process recovery failed on attempt $attempt/${MaxRecoveryAttempts}: $($_.Exception.Message)"
            Write-Host $msg
            if ($attempt -ge $MaxRecoveryAttempts) {
                Send-HealthAlert -ExitCode 3 -Message $msg -BeforeState $before
                Write-HealthLog -ExitCode 3 -Message $msg -BeforeState $before
                exit 3
            }
            continue
        }
        $after = Wait-RunnerOnline -RepoName $Repo -TargetRunnerName $RunnerName -PollSeconds $RecoveryPollSeconds
        if ($null -eq $after) {
            $msg = "Runner disappeared after process start attempt $attempt/${MaxRecoveryAttempts}: $RunnerName"
            Write-Host $msg
            if ($attempt -ge $MaxRecoveryAttempts) {
                Send-HealthAlert -ExitCode 5 -Message $msg -BeforeState $before
                Write-HealthLog -ExitCode 5 -Message $msg -BeforeState $before
                exit 5
            }
            continue
        }
        Write-Host "Runner status after process recovery attempt $attempt/${MaxRecoveryAttempts}: name=$($after.name) status=$($after.status) busy=$($after.busy)"
        if ($after.status -eq "online") {
            Write-Host "Runner recovery successful (process mode)."
            Write-HealthLog -ExitCode 0 -Message "Runner recovery successful (process mode)." -BeforeState $before -AfterState $after
            exit 0
        }
    }
    $msg = "Runner is still offline after process-start retries."
    Write-Host $msg
    Send-HealthAlert -ExitCode 6 -Message $msg -BeforeState $before -AfterState $after
    Write-HealthLog -ExitCode 6 -Message $msg -BeforeState $before -AfterState $after
    exit 6
}

Write-Host "Attempting service restart: $($svc.Name) (max_attempts=$MaxRecoveryAttempts)"
for ($attempt = 1; $attempt -le $MaxRecoveryAttempts; $attempt++) {
    try {
        Restart-Service -Name $svc.Name -ErrorAction Stop
    }
    catch {
        $msg = "Restart-Service failed on attempt $attempt/${MaxRecoveryAttempts}: $($_.Exception.Message)"
        Write-Host $msg
        if ($attempt -ge $MaxRecoveryAttempts) {
            Send-HealthAlert -ExitCode 4 -Message $msg -BeforeState $before -ServiceName $svc.Name
            Write-HealthLog -ExitCode 4 -Message $msg -BeforeState $before -ServiceName $svc.Name
            exit 4
        }
        continue
    }
    $after = Wait-RunnerOnline -RepoName $Repo -TargetRunnerName $RunnerName -PollSeconds $RecoveryPollSeconds
    if ($null -eq $after) {
        $msg = "Runner disappeared after restart attempt $attempt/${MaxRecoveryAttempts}: $RunnerName"
        Write-Host $msg
        if ($attempt -ge $MaxRecoveryAttempts) {
            Send-HealthAlert -ExitCode 5 -Message $msg -BeforeState $before -ServiceName $svc.Name
            Write-HealthLog -ExitCode 5 -Message $msg -BeforeState $before -ServiceName $svc.Name
            exit 5
        }
        continue
    }
    Write-Host "Runner status after service recovery attempt $attempt/${MaxRecoveryAttempts}: name=$($after.name) status=$($after.status) busy=$($after.busy)"
    if ($after.status -eq "online") {
        Write-Host "Runner recovery successful."
        Write-HealthLog -ExitCode 0 -Message "Runner recovery successful." -BeforeState $before -AfterState $after -ServiceName $svc.Name
        exit 0
    }
}

$msg = "Runner is still offline after restart retries."
Write-Host $msg
Send-HealthAlert -ExitCode 6 -Message $msg -BeforeState $before -AfterState $after -ServiceName $svc.Name
Write-HealthLog -ExitCode 6 -Message $msg -BeforeState $before -AfterState $after -ServiceName $svc.Name
exit 6
