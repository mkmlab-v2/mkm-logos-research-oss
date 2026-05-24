<#
.SYNOPSIS
  Register weekly Scheduled Task: Logos chronology overlay + Oracle v3 static deploy (local bundle, optional VPS sync).

.DESCRIPTION
  Runs: build_logos_chronology_v2_ai_synthesis_v1.py --write-ssot, then Invoke-LogosChronologyParallelBundle_v1.ps1 (no -RebuildChronology; preserves v2 SSOT).
  Default: Sunday 08:30 local (after compression governance 07:00 if both registered).

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Scheduled task name (default: MKM_Logos_Chronology_WeeklyBundle).

.PARAMETER SundayAt
  Local time HH:mm for weekly Sunday trigger (default: 08:30).

.PARAMETER SkipVpsSync
  Pass -SkipVpsSync to the bundle (staging only).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Logos_Chronology_WeeklyBundle",
    [string]$SundayAt = "08:30",
    [switch]$SkipVpsSync
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$buildV2 = Join-Path $workspaceRoot "scripts\build_logos_chronology_v2_ai_synthesis_v1.py"
$runner = Join-Path $workspaceRoot "scripts\Invoke-LogosChronologyParallelBundle_v1.ps1"

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
    throw "SundayAt must be HH:mm (e.g. 08:30), got: $SundayAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command ""& { py '$buildV2' --write-ssot; if (`$LASTEXITCODE -ne 0) { exit `$LASTEXITCODE }; & '$runner'$(if ($SkipVpsSync) { ' -SkipVpsSync' }) }"""
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $argLine `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Weekly: rebuild logos chronology SSOT, merge era QA presets, deploy showroom staging, sync jemaai.cloud Oracle v3 static."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (weekly Sunday $SundayAt, user=$env:USERNAME)"
Write-Host "Chain: py $buildV2 --write-ssot -> $runner$(if ($SkipVpsSync) { ' -SkipVpsSync' })"
