<#
.SYNOPSIS
  Register (or remove) a daily Scheduled Task for MASK HYPO passive cross-audit (HYPO-4).

.DESCRIPTION
  Runs: scripts/Run-CompressionMaskHypoPassiveCrossAudit_v1.ps1
  Compression-dedicated B-track lane — NOT KOSPI Evening prophecy / BTrack-DailyHypothesis.

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Default: MKM_Compression_MaskHypoPassiveCrossAudit_Daily

.PARAMETER DailyAt
  Local time HH:mm (default: 03:15).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Compression_MaskHypoPassiveCrossAudit_Daily",
    [string]$DailyAt = "03:15"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Run-CompressionMaskHypoPassiveCrossAudit_v1.ps1"

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
    throw "DailyAt must be HH:mm (e.g. 03:15), got: $DailyAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$workspaceRoot`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $argLine `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Daily -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Daily: MASK HYPO passive cross-audit (registry + BIZ/CS overlay/shadow). B-track only; non-gating."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (daily $DailyAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"
Write-Host "SSOT tier: tier4_solo_intentional_keep (mkm_scheduler_solo_core_stack_v1.json)"
