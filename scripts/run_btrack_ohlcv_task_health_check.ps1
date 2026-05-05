param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM-BTrack-OHLCV-ScoreEval-Daily",
    [int]$MaxArtifactAgeHours = 26
)

$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $WorkspaceRoot

$artifactsDir = Join-Path $WorkspaceRoot "docs\final\artifacts"
$scorePath = Join-Path $artifactsDir "btrack_prophecy_score_latest.json"
$evalPath = Join-Path $artifactsDir "prophecy_hit_rate_eval_latest.json"
$healthOut = Join-Path $artifactsDir "btrack_ohlcv_task_health_latest.json"
$alertOut = Join-Path $artifactsDir "btrack_ohlcv_task_health_alert_latest.json"

function Get-IsoUtc([datetime]$dt) {
    return $dt.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
}

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction Stop

$now = Get-Date

function Get-ArtifactState([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) {
        return [pscustomobject]@{
            exists = $false
            path = $path
            mtime_local = $null
            mtime_utc = $null
            age_hours = $null
            stale = $true
        }
    }
    $it = Get-Item -LiteralPath $path
    $age = ($now - $it.LastWriteTime).TotalHours
    return [pscustomobject]@{
        exists = $true
        path = $path
        mtime_local = $it.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
        mtime_utc = Get-IsoUtc $it.LastWriteTime
        age_hours = [math]::Round($age, 3)
        stale = ($age -gt $MaxArtifactAgeHours)
    }
}

$score = Get-ArtifactState $scorePath
$eval = Get-ArtifactState $evalPath

$warnings = @()
if ($task.State -ne "Ready" -and $task.State -ne "Running") {
    $warnings += "task_state_not_ready_or_running:$($task.State)"
}
if ($taskInfo.LastTaskResult -ne 0 -and $taskInfo.LastTaskResult -ne 267011) {
    # 267011 is expected before first run on some systems.
    $warnings += "last_task_result_nonzero:$($taskInfo.LastTaskResult)"
}
if ($score.stale) { $warnings += "score_artifact_stale_or_missing" }
if ($eval.stale) { $warnings += "eval_artifact_stale_or_missing" }

$status = if ($warnings.Count -eq 0) { "ok" } else { "warn" }

$payload = [ordered]@{
    schema = "btrack_ohlcv_task_health_v1"
    generated_at_utc = Get-IsoUtc $now
    task = [ordered]@{
        name = $TaskName
        state = "$($task.State)"
        enabled = $task.Settings.Enabled
        hidden = $task.Settings.Hidden
        next_run_time_local = $taskInfo.NextRunTime.ToString("yyyy-MM-dd HH:mm:ss")
        last_run_time_local = $taskInfo.LastRunTime.ToString("yyyy-MM-dd HH:mm:ss")
        last_task_result = $taskInfo.LastTaskResult
    }
    artifacts = [ordered]@{
        score = $score
        eval = $eval
    }
    max_artifact_age_hours = $MaxArtifactAgeHours
    status = $status
    warnings = $warnings
}

$json = $payload | ConvertTo-Json -Depth 8
$json | Set-Content -LiteralPath $healthOut -Encoding UTF8

$alert = [ordered]@{
    schema = "btrack_ohlcv_task_health_alert_v1"
    generated_at_utc = Get-IsoUtc $now
    status = $status
    warning_count = $warnings.Count
    warnings = $warnings
}
($alert | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $alertOut -Encoding UTF8

Write-Host "WROTE: $healthOut"
Write-Host "WROTE: $alertOut"
Write-Host "status: $status"
if ($warnings.Count -gt 0) {
    $warnings | ForEach-Object { Write-Host "WARN: $_" -ForegroundColor Yellow }
}

