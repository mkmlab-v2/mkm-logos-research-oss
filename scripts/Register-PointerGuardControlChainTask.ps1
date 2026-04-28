<#
.SYNOPSIS
  Register (or remove) a daily Scheduled Task for PointerGuard control chain.

.PARAMETER Remove
  Unregister the task.

.PARAMETER DryRun
  Print registration details without creating/removing task.

.PARAMETER TaskName
  Scheduled task name.

.PARAMETER DailyAt
  Local time HH:mm for daily trigger.
#>
param(
    [switch]$Remove,
    [switch]$DryRun,
    [string]$TaskName = "MKM_PointerGuard_ControlChain_Daily",
    [string]$DailyAt = "06:30",
    [string]$RouterTargetPath = "reports/demo_run.json",
    [string]$MemoryTuningTargetPath = "projects/bitcoin-trading/memory/v2/demo.json",
    [string]$WeeklyP0DrillDay = "Sunday"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_pointerguard_control_chain_daily.ps1"

if ($Remove) {
    if ($DryRun) {
        Write-Host "[DryRun] Would remove scheduled task: $TaskName"
        exit 0
    }
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $DailyAt -split ':'
if ($parts.Count -lt 2) {
    throw "DailyAt must be HH:mm (e.g. 06:30), got: $DailyAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -RouterTargetPath `"$RouterTargetPath`" -MemoryTuningTargetPath `"$MemoryTuningTargetPath`" -WeeklyP0DrillDay `"$WeeklyP0DrillDay`""
$description = "Daily PointerGuard control chain with security-first hardening (policy/ramp/freeze/runtime/smoke + C1/C6/non-exposure checklist)."

if ($DryRun) {
    Write-Host "[DryRun] TaskName: $TaskName"
    Write-Host "[DryRun] Trigger : Daily at $DailyAt"
    Write-Host "[DryRun] Runner  : $runner"
    Write-Host "[DryRun] Args    : $argLine"
    Write-Host "[DryRun] P0 Drill: Weekly day=$WeeklyP0DrillDay"
    Write-Host "[DryRun] Desc    : $description"
    exit 0
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $argLine `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Daily -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (daily $DailyAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"
