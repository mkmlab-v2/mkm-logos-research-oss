<#
.SYNOPSIS
  Register (or remove) weekly scheduled task for Layer1/Layer5 maintenance chain.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Layer1Layer5_WeeklyMaintenance",
    [ValidateSet("MON","TUE","WED","THU","FRI","SAT","SUN")]
    [string]$WeeklyDay = "SUN",
    [string]$WeeklyAt = "08:30",
    [int]$SampleSize = 50,
    [int]$Seed = 42,
    [int]$MinApprovedSamples = 50
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_layer1_layer5_weekly_maintenance_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $WeeklyAt -split ':'
if ($parts.Count -lt 2) { throw "WeeklyAt must be HH:mm, got: $WeeklyAt" }

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$workspaceRoot`" -SampleSize $SampleSize -Seed $Seed -MinApprovedSamples $MinApprovedSamples"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $workspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek $WeeklyDay -At $WeeklyAt
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 45)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Weekly Layer1/Layer5 maintenance chain with emotion+memory governance."
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (weekly $WeeklyDay $WeeklyAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"
