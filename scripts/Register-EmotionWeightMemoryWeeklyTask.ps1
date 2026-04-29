<#
.SYNOPSIS
  Register (or remove) weekly scheduled task for emotion-weighted memory report.

.DESCRIPTION
  Runs:
    C:\workspace\scripts\run_emotion_weight_memory_weekly_chain.ps1

  Passes -PromotionWindowSize (default 4) for rolling human-gate readiness in the runner.

  Default:
    TaskName = MKM_EmotionWeightMemory_Weekly
    WeeklyOn = MON
    At = 08:40
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_EmotionWeightMemory_Weekly",
    [ValidateSet("MON","TUE","WED","THU","FRI","SAT","SUN")]
    [string]$WeeklyOn = "MON",
    [string]$At = "08:40",
    [string]$InputJsonl = "C:\workspace\docs\final\dummy_swarm_score.jsonl",
    [string]$LabelsJsonl = "",
    [switch]$UseOperationalBuilders,
    [int]$PromotionWindowSize = 4
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_emotion_weight_memory_weekly_chain.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $At -split ':'
if ($parts.Count -lt 2) {
    throw "At must be HH:mm, got: $At"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
if ($hour -lt 0 -or $hour -gt 23 -or $minute -lt 0 -or $minute -gt 59) {
    throw "At out of range (HH:mm): $At"
}

$dayMap = @{
    "MON" = "Monday"
    "TUE" = "Tuesday"
    "WED" = "Wednesday"
    "THU" = "Thursday"
    "FRI" = "Friday"
    "SAT" = "Saturday"
    "SUN" = "Sunday"
}
$daysOfWeek = $dayMap[$WeeklyOn]

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -InputJsonl `"$InputJsonl`""
if ($LabelsJsonl -and (Test-Path -LiteralPath $LabelsJsonl)) {
    $argLine += " -LabelsJsonl `"$LabelsJsonl`""
}
if ($UseOperationalBuilders) {
    $argLine += " -BuildOperationalInputs"
}
$argLine += " -PromotionWindowSize $PromotionWindowSize"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $workspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $daysOfWeek -At $At
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 45)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Weekly emotion-weighted memory event build + contribution evaluation report."
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description $description `
    -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName"
Write-Host "WeeklyOn: $WeeklyOn ($daysOfWeek) At: $At"
Write-Host "Runner: $runner"
Write-Host "InputJsonl: $InputJsonl"
Write-Host "PromotionWindowSize: $PromotionWindowSize"
if ($LabelsJsonl) {
    Write-Host "LabelsJsonl: $LabelsJsonl"
}
if ($UseOperationalBuilders) {
    Write-Host "Mode: UseOperationalBuilders=true"
}

