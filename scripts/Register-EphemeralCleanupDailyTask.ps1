<#
.SYNOPSIS
  Register (or remove) a daily Scheduled Task for ephemeral workspace cleanup.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "Workspace_EphemeralCleanup_Daily",
    [string]$DailyAt = "04:40",
    [int]$RetentionDays = 3,
    [int]$MaxDeleteCount = 0,
    [switch]$IncludeTmp
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Invoke-EphemeralCleanup.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $DailyAt -split ':'
if ($parts.Count -lt 2) {
    throw "DailyAt must be HH:mm (e.g. 04:40), got: $DailyAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$base = Get-Date
$atToday = Get-Date -Year $base.Year -Month $base.Month -Day $base.Day -Hour $hour -Minute $minute -Second 0

$arg = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -RetentionDays $RetentionDays"
if ($MaxDeleteCount -gt 0) {
    $arg += " -MaxDeleteCount $MaxDeleteCount"
}
if ($IncludeTmp) {
    $arg += " -IncludeTmp"
}
$arg += " -Apply"

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg -WorkingDirectory $workspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $atToday
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "Daily cleanup for ephemeral workspace files and temp folders."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (daily at $DailyAt, retention=$RetentionDays days)"
Write-Host "Runner: $runner"
