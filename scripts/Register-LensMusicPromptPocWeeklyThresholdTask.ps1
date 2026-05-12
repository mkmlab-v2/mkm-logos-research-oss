<#
.SYNOPSIS
  Register (or remove) weekly scheduled task for lens-music prompt PoC threshold chain.

.DESCRIPTION
  Runs:
    C:\workspace\scripts\Run-LensMusicPromptPocWeeklyThresholdChain_v1.ps1

  Default:
    TaskName = MKM_LensMusicPromptPoc_WeeklyThreshold
    WeeklyOn = SUN
    At = 07:20
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_LensMusicPromptPoc_WeeklyThreshold",
    [ValidateSet("MON","TUE","WED","THU","FRI","SAT","SUN")]
    [string]$WeeklyOn = "SUN",
    [string]$At = "07:20",
    [switch]$SkipDashboard
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Run-LensMusicPromptPocWeeklyThresholdChain_v1.ps1"

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

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`""
if ($SkipDashboard) {
    $argLine += " -SkipDashboard"
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $workspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $daysOfWeek -At $At
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 45)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Weekly lens-music prompt PoC threshold sweep/apply/policy chain. Optional: set User env MKM_APPROVAL_TICKET_REQUIRED=1 and place docs/final/artifacts/mkm_approval_ticket_v1_latest.json (see docs/final/schemas/mkm_approval_ticket_v1.example.json)."
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
if ($SkipDashboard) {
    Write-Host "Mode: SkipDashboard=true"
}
