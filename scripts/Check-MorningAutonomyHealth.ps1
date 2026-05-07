param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== Morning Autonomy Health Snapshot ===" -ForegroundColor Cyan

$taskNames = @(
    "MKM_AIV2_DailyReadiness",
    "MKM_AIV2_FinalOpsGuard_Daily",
    "MKM-TrackC-MacroDailyFusion",
    "SASANG_4AGENT_DailyMonitor",
    "Bitcoin-WaitingQueue-BTCBinance-Daily-Strict",
    "Bitcoin-WaitingQueue-DualMarket-Daily-Strict"
)

$taskRows = Get-ScheduledTask |
    Where-Object { $taskNames -contains $_.TaskName } |
    ForEach-Object {
        $task = $_
        $info = Get-ScheduledTaskInfo -TaskName $task.TaskName
        [PSCustomObject]@{
            TaskName       = $task.TaskName
            State          = $task.State
            LastTaskResult = $info.LastTaskResult
            LastRunTime    = $info.LastRunTime
            NextRunTime    = $info.NextRunTime
        }
    } |
    Sort-Object TaskName

$taskRows | Format-Table -AutoSize

Write-Host ""
Write-Host "=== Critical Artifacts ===" -ForegroundColor Cyan

$artifactPaths = @(
    "docs\final\artifacts\sasang_4agent_monitor_policy_v1.json",
    "docs\final\artifacts\sasang_4agent_daily_monitor_run_latest.json",
    "docs\final\artifacts\mkm_ai_v2_readiness_latest.json",
    "docs\final\artifacts\mkm_ai_final_ops_bundle_latest.json",
    "docs\final\artifacts\mkm_trackc_client_handoff_guard_latest.json",
    "docs\final\artifacts\security_secret_exposure_survey_latest.json"
)

$artifactRows = foreach ($relative in $artifactPaths) {
    $full = Join-Path $WorkspaceRoot $relative
    if (Test-Path -LiteralPath $full) {
        $item = Get-Item -LiteralPath $full
        [PSCustomObject]@{
            Artifact = $relative
            Exists   = $true
            Updated  = $item.LastWriteTime
        }
    }
    else {
        [PSCustomObject]@{
            Artifact = $relative
            Exists   = $false
            Updated  = $null
        }
    }
}

$artifactRows | Format-Table -AutoSize

$failedTasks = @($taskRows | Where-Object { $_.LastTaskResult -ne 0 })
$missingArtifacts = @($artifactRows | Where-Object { -not $_.Exists })

Write-Host ""
if ($failedTasks.Count -eq 0 -and $missingArtifacts.Count -eq 0) {
    Write-Host "RESULT: OK (all watched tasks/artifacts healthy)" -ForegroundColor Green
    exit 0
}

Write-Host "RESULT: CHECK REQUIRED" -ForegroundColor Yellow
if ($failedTasks.Count -gt 0) {
    Write-Host "- Non-zero LastTaskResult tasks:" -ForegroundColor Yellow
    $failedTasks | Select-Object TaskName, LastTaskResult, LastRunTime | Format-Table -AutoSize
}
if ($missingArtifacts.Count -gt 0) {
    Write-Host "- Missing artifacts:" -ForegroundColor Yellow
    $missingArtifacts | Select-Object Artifact | Format-Table -AutoSize
}

exit 1
