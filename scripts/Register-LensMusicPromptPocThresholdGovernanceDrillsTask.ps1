<#
.SYNOPSIS
  Register (or remove) weekly governance drill task for lens-music prompt PoC threshold webhook flow.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_LensMusicPromptPoc_ThresholdGovernanceDrills_Weekly",
    [ValidateSet("MON","TUE","WED","THU","FRI","SAT","SUN")]
    [string]$WeeklyOn = "SUN",
    [string]$At = "07:40",
    [switch]$SkipDashboard
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Run-LensMusicPromptPocThresholdGovernanceDrills_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$dayMap = @{
    "MON" = "Monday"; "TUE" = "Tuesday"; "WED" = "Wednesday"; "THU" = "Thursday"
    "FRI" = "Friday"; "SAT" = "Saturday"; "SUN" = "Sunday"
}
$daysOfWeek = $dayMap[$WeeklyOn]

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`""
if ($SkipDashboard) { $argLine += " -SkipDashboard" }

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $workspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $daysOfWeek -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Weekly lens-music threshold webhook governance drills (best-effort + strict). Optional: MKM_APPROVAL_TICKET_REQUIRED=1 + mkm_approval_ticket_v1_latest.json." -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName"
Write-Host "WeeklyOn: $WeeklyOn ($daysOfWeek) At: $At"
Write-Host "Runner: $runner"
