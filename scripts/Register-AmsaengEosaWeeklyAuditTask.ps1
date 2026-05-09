[CmdletBinding()]
param(
    [switch]$Remove,
    [switch]$StartNow,
    [string]$TaskName = "MKM-AmsaengEosa-Weekly-Audit-Packet",
    [string]$RunAt = "08:30",
    [int]$RestartCount = 3,
    [int]$RestartIntervalMinutes = 5
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$runner = Join-Path $PSScriptRoot "Run-AmsaengEosaWeeklyAuditTask.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "scheduled_task: REMOVED ($TaskName)"
    exit 0
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runner`""
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At ([datetime]::ParseExact($RunAt, "HH:mm", $null))
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -RestartCount ([Math]::Max(0, $RestartCount)) `
    -RestartInterval (New-TimeSpan -Minutes ([Math]::Max(1, $RestartIntervalMinutes)))

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Write-Output "scheduled_task: REGISTERED ($TaskName)"
Write-Output "run_at=$RunAt (Sunday)"
Write-Output "restart_count=$([Math]::Max(0, $RestartCount))"
Write-Output "restart_interval_minutes=$([Math]::Max(1, $RestartIntervalMinutes))"

if ($StartNow) {
    Start-ScheduledTask -TaskName $TaskName
    Write-Output "scheduled_task: STARTED ($TaskName)"
}
