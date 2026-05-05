param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM-BTrack-OHLCV-Health-Daily",
    [string]$StartTime = "08:55",
    [string]$MonitoredTaskName = "MKM-BTrack-OHLCV-ScoreEval-Daily",
    [int]$MaxArtifactAgeHours = 26,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[DONE] Removed task (if existed): $TaskName" -ForegroundColor Yellow
    exit 0
}

$scriptPath = Join-Path $WorkspaceRoot "scripts\run_btrack_ohlcv_task_health_check.ps1"
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Missing script: $scriptPath"
}

$args = @(
    "-NoProfile",
    "-WindowStyle", "Hidden",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$scriptPath`"",
    "-WorkspaceRoot", "`"$WorkspaceRoot`"",
    "-TaskName", "`"$MonitoredTaskName`"",
    "-MaxArtifactAgeHours", "$MaxArtifactAgeHours"
) -join " "

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $args -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $StartTime
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew `
    -Hidden
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited
$registeredLogon = "S4U"
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description "Daily hidden health check for B-track OHLCV score/eval scheduler." `
        -Force | Out-Null
}
catch {
    # Non-admin shells can fail with AccessDenied on S4U. Fallback to Interactive.
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description "Daily hidden health check for B-track OHLCV score/eval scheduler." `
        -Force | Out-Null
    $registeredLogon = "Interactive"
    Write-Warning "S4U registration failed; fallback to Interactive mode."
}

$taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "[DONE] Registered task: $TaskName" -ForegroundColor Green
Write-Host "StartTime: $StartTime"
Write-Host "NextRunTime: $($taskInfo.NextRunTime)"
Write-Host "LogonType: $registeredLogon"
