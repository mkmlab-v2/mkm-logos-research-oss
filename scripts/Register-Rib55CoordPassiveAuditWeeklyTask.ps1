<#
.SYNOPSIS
  Register weekly Scheduled Task for rib55 + COORD passive audit.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Rib55_CoordPassiveAudit_Weekly",
    [string]$SundayAt = "06:45"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Run-Rib55CoordPassiveAuditWeekly_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $SundayAt -split ':'
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$workspaceRoot`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $workspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "Weekly: rib55 render + L0/L1 ablation + coord v2 + v2 stub COORD roundtrip. HYPO; non-gating."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $description -Force | Out-Null

$taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "Registered scheduled task: $TaskName (weekly Sunday $SundayAt)"
Write-Host "  NextRunTime: $($taskInfo.NextRunTime)"
Write-Host "SSOT tier: tier4_solo_intentional_keep"
