<#
.SYNOPSIS
  Register (or remove) a weekly Scheduled Task for compression governance (ultra default + KPI + dated report).

.DESCRIPTION
  Runs: scripts/run_compression_weekly_governance_chain.ps1 (Track A + Track B literal + governance JSON).
  Default: Sunday 07:00 local time. Adjust -SundayAt if it collides with other weekly jobs.

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Scheduled task name (default: MKM_Compression_WeeklyGovernance).

.PARAMETER SundayAt
  Local time HH:mm for weekly Sunday trigger (default: 07:00).

.PARAMETER SkipLiteralTrack
  If set, the scheduled action passes -SkipLiteralTrack (Track A only).

.PARAMETER IncludeStatelessTrustPacket
  If set, weekly chain also runs customer PoC + lossless stateless smoke (pytest/golden skipped; chain already ran them).

.PARAMETER RunWhenLoggedOff
  Use S4U principal so Sunday 07:00 can run without an interactive session (elevated register recommended).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Compression_WeeklyGovernance",
    [string]$SundayAt = "07:00",
    [switch]$SkipLiteralTrack,
    [switch]$IncludeStatelessTrustPacket,
    [switch]$RunWhenLoggedOff
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_compression_weekly_governance_chain.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $SundayAt -split ':'
if ($parts.Count -lt 2) {
    throw "SundayAt must be HH:mm (e.g. 07:00), got: $SundayAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`""
if ($SkipLiteralTrack) {
    $argLine += " -SkipLiteralTrack"
}
if ($IncludeStatelessTrustPacket) {
    $argLine += " -IncludeStatelessTrustPacket"
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $argLine `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

$logonType = if ($RunWhenLoggedOff) { "S4U" } else { "Interactive" }
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType $logonType -RunLevel Limited

$description = "Weekly: run_ultra_compression_default (universal+literal), KPI summary, loss patterns, compression_weekly_governance_report_YYYY-MM-DD.json + latest. Optional -IncludeStatelessTrustPacket: customer PoC + lossless stateless smoke."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

$taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "Registered scheduled task: $TaskName (weekly Sunday $SundayAt, user=$env:USERNAME, logon=$logonType)"
Write-Host "  NextRunTime: $($taskInfo.NextRunTime)"
Write-Host "Runner: $runner"
if ($SkipLiteralTrack) {
    Write-Host "Note: task uses -SkipLiteralTrack (Track A only)."
}
