param(
    [string]$TaskName = "Bitcoin-FatalAlert-Healthcheck-Weekly",
    [string]$StartTime = "09:05",
    [switch]$Send,
    [ValidateSet("DAILY", "WEEKLY")]
    [string]$Schedule = "DAILY",
    [ValidateSet("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")]
    [string]$WeeklyDay = "MON"
)

$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$checker = Join-Path $projectRoot "ops\windows-rehearsal\test_fatal_alert_channels.ps1"

if (-not (Test-Path $checker)) {
    throw "Fatal alert healthcheck script not found: $checker"
}

$sendArg = if ($Send) { " -Send" } else { "" }
$tr = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$checker`"$sendArg"

schtasks /Delete /TN $TaskName /F | Out-Null 2>&1
if ($Schedule -eq "WEEKLY") {
    schtasks /Create /TN $TaskName /SC WEEKLY /D $WeeklyDay /ST $StartTime /TR $tr /F | Out-Null
} else {
    schtasks /Create /TN $TaskName /SC DAILY /ST $StartTime /TR $tr /F | Out-Null
}
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create scheduled task. ExitCode=$LASTEXITCODE"
}

Write-Host "Created scheduled task: $TaskName"
Write-Host "Start time: $StartTime"
Write-Host "Mode: $(if ($Send) { "send" } else { "dry_run" })"
$scheduleLabel = if ($Schedule -eq "WEEKLY") { "$Schedule ($WeeklyDay)" } else { $Schedule }
Write-Host "Schedule: $scheduleLabel"
Write-Host "Command: $tr"
exit 0
