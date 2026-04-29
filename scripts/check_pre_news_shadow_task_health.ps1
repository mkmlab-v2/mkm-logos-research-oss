param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM-PreNews-Shadow-Daily",
    [string]$OutJson = "docs/final/artifacts/pre_news_shadow_task_health_latest.json"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    throw "Scheduled task not found: $TaskName"
}
$info = Get-ScheduledTaskInfo -TaskName $TaskName

$resultCode = [int64]($info.LastTaskResult)
$resultHex = ("0x{0:X8}" -f ([uint32]$resultCode))
$u = [uint32]$resultCode
# Treat Task Scheduler informational range (0x41300~0x4130F) as non-error.
$isSchedulerInfo = ($u -ge 0x41300 -and $u -le 0x4130F)
$isHealthy = ($resultCode -eq 0 -or $isSchedulerInfo)

$payload = [ordered]@{
    schema = "pre_news_shadow_task_health_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    task_name = $TaskName
    state = [string]$task.State
    last_run_time = if ($info.LastRunTime) { $info.LastRunTime.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") } else { $null }
    next_run_time = if ($info.NextRunTime) { $info.NextRunTime.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") } else { $null }
    last_task_result = $resultCode
    last_task_result_hex = $resultHex
    healthy = $isHealthy
    result_category = if ($resultCode -eq 0) { "OK" } elseif ($isSchedulerInfo) { "SchedulerInfo" } else { "NonZero" }
    note = "Task Scheduler health snapshot for pre-news shadow daily runner."
}

$outPath = Join-Path $WorkspaceRoot $OutJson
$outDir = Split-Path -Parent $outPath
if (-not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

($payload | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath $outPath -Encoding UTF8
Write-Host "Wrote: $outPath"
if (-not $isHealthy) {
    Write-Warning "Task is not healthy. LastTaskResult=$resultCode ($resultHex)"
}

