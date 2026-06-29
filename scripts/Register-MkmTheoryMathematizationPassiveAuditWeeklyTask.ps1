<#
.SYNOPSIS
  Register (or remove) weekly Scheduled Task for theory mathematization passive audit.

.DESCRIPTION
  Runs: scripts/Run-MkmTheoryMathematizationPassiveAuditWeekly_v1.ps1
  NL guard (MCP) + phase3 smoke + promotion gate dry-run. B-track only; non-gating.

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Default: MKM_TheoryMathematization_PassiveAudit_Weekly

.PARAMETER SundayAt
  Local time HH:mm (default: 06:15).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_TheoryMathematization_PassiveAudit_Weekly",
    [string]$SundayAt = "06:15"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Run-MkmTheoryMathematizationPassiveAuditWeekly_v1.ps1"

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
    throw "SundayAt must be HH:mm (e.g. 06:15), got: $SundayAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$workspaceRoot`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $argLine `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Weekly: theory mathematization passive audit (NL guard MCP + phase3 + promotion gate dry-run). B-track only."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

$taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "Registered scheduled task: $TaskName (weekly Sunday $SundayAt, user=$env:USERNAME)"
Write-Host "  NextRunTime: $($taskInfo.NextRunTime)"
Write-Host "Runner: $runner"
Write-Host "SSOT tier: tier4_solo_intentional_keep (mkm_scheduler_solo_core_stack_v1.json)"
