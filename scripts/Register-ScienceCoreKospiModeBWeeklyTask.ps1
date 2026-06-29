<#
.SYNOPSIS
  Register weekly KOSPI Mode B research task (shock/calm + news ablation).

.DESCRIPTION
  Complements MKM_ScienceCore_WeeklyGovernance (Sunday full bundle).
  Default: Wednesday 09:05 local — skips daily passive (Mon–Fri daily chain covers OHLCV).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_ScienceCore_KospiModeB_Weekly",
    [string]$WednesdayAt = "09:05"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Run-ScienceCoreKospiModeBResearch_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $WednesdayAt -split ':'
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File ""$runner"" -SkipDailyPassive"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $workspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Wednesday -At $at
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Enable-ScheduledTask -TaskName $TaskName | Out-Null
Write-Host "Registered (Enabled): $TaskName (Wednesday $WednesdayAt) -> Run-ScienceCoreKospiModeBResearch_v1.ps1 -SkipDailyPassive"
