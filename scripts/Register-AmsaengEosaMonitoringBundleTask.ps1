[CmdletBinding()]
param(
    [switch]$Remove,
    [switch]$StartNow,
    [string]$TaskName = "MKM-AmsaengEosa-Monitoring-Bundle-60min",
    [int]$IntervalMinutes = 60,
    [int]$RestartCount = 3,
    [int]$RestartIntervalMinutes = 5,
    # Run-AmsaengEosaMonitoringBundleTask.ps1 -GovernanceSoftFail (거버넌스만 실패 무시; 기본은 엄격)
    [switch]$GovernanceSoftFail
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$runner = Join-Path $PSScriptRoot "Run-AmsaengEosaMonitoringBundleTask.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "scheduled_task: REMOVED ($TaskName)"
    exit 0
}

$interval = [Math]::Max(1, $IntervalMinutes)
$govArg = if ($GovernanceSoftFail) { " -GovernanceSoftFail" } else { "" }
$runCmd = "cmd.exe /c powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$runner`"$govArg && exit /b 0"

schtasks /Create /TN $TaskName /TR $runCmd /SC MINUTE /MO $interval /RL LIMITED /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to register task: $TaskName (exit=$LASTEXITCODE)"
}

# Apply retry and concurrency policy using ScheduledTasks cmdlets.
# - RestartCount/RestartInterval: automatic retries on failure.
# - MultipleInstances IgnoreNew: prevent overlapping runs.
try {
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Minutes $interval) -RepetitionDuration (New-TimeSpan -Days 3650)
    $argForCmd = "/c powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$runner`"$govArg && exit /b 0"
    $action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $argForCmd
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -MultipleInstances IgnoreNew `
        -RestartCount ([Math]::Max(0, $RestartCount)) `
        -RestartInterval (New-TimeSpan -Minutes ([Math]::Max(1, $RestartIntervalMinutes)))
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
}
catch {
    Write-Warning "retry_policy_apply_failed task=$TaskName error=$($_.Exception.Message)"
}

Write-Output "scheduled_task: REGISTERED ($TaskName)"
Write-Output "interval_minutes=$interval"
Write-Output "governance_soft_fail=$GovernanceSoftFail"
Write-Output "restart_count=$([Math]::Max(0, $RestartCount))"
Write-Output "restart_interval_minutes=$([Math]::Max(1, $RestartIntervalMinutes))"

if ($StartNow) {
    Start-ScheduledTask -TaskName $TaskName
    Write-Output "scheduled_task: STARTED ($TaskName)"
}
