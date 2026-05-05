param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM-PreNews-Shadow-Health-Daily",
    [string]$StartTime = "06:50",
    [string]$MonitoredTaskName = "MKM-PreNews-Shadow-Daily"
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $WorkspaceRoot "scripts/run_pre_news_shadow_health_chain.ps1"
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Missing script: $scriptPath"
}

$args = @(
    "-NoProfile",
    "-WindowStyle", "Hidden",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$scriptPath`"",
    "-WorkspaceRoot", "`"$WorkspaceRoot`"",
    "-TaskName", "`"$MonitoredTaskName`""
) -join " "

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $args -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $StartTime
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Daily health check + alert gate for pre-news shadow scheduler task." `
    -Force | Out-Null

Write-Host "OK: Scheduled health task registered: $TaskName" -ForegroundColor Green
Write-Host "StartTime: $StartTime"

