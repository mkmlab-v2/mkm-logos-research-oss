#Requires -Version 5.1
<#
.SYNOPSIS
  Register (or remove) daily Scheduled Task: Aramaic MVP chain + audit JSONL append.

.DESCRIPTION
  Invokes scripts/run_aramaic_mvp_now_with_audit.ps1 with -NoWebhook and -SkipLogosInsightBundle (cold-host default).
  By default appends -SurvivorHealthAlertDryRun so scheduled runs skip survivor-health POST (--dry-run).
  Use -OmitSurvivorHealthAlertDryRun to register without that flag (live webhook path; operator choice).
  Direct chain-only runs: env MKM_ARAMAIC_SURVIVOR_HEALTH_ALERT_DRY_RUN=1|true|yes (Process/User/Machine) is read by run_aramaic_mvp_chain_v1.ps1 without this register script.
  Re-register with the same -TaskName overwrites. SSOT: CONSTITUTION Aramaic MVP ops table.

.PARAMETER Remove
  Unregister the task.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM-AramaicMvp-DailyAudit",
    [string]$DailyAt = "06:15",
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$RunWhenLoggedOff,
    # Back-compat: previously required to append -SurvivorHealthAlertDryRun; now default-on (ignored if passed).
    [switch]$SurvivorHealthAlertDryRun,
    [switch]$OmitSurvivorHealthAlertDryRun
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\run_aramaic_mvp_now_with_audit.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing runner: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[DONE] Removed task (if existed): $TaskName" -ForegroundColor Yellow
    exit 0
}

$parts = $DailyAt -split ':'
if ($parts.Count -lt 2) {
    throw "DailyAt must be HH:mm (e.g. 06:15), got: $DailyAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$base = Get-Date
$atToday = Get-Date -Year $base.Year -Month $base.Month -Day $base.Day -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`" -NoWebhook -SkipLogosInsightBundle"
if (-not $OmitSurvivorHealthAlertDryRun) {
    $argLine += " -SurvivorHealthAlertDryRun"
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $atToday
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 90) `
    -MultipleInstances IgnoreNew `
    -Hidden

$logonType = if ($RunWhenLoggedOff) { "S4U" } else { "Interactive" }
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType $logonType -RunLevel Limited
$dry = if ($OmitSurvivorHealthAlertDryRun) { " (survivor health: live POST allowed)." } else { " -SurvivorHealthAlertDryRun (Track T survivor POST skipped)." }
$desc = "Daily Aramaic MVP chain + audit log append (B-track; not trading). -NoWebhook -SkipLogosInsightBundle$dry"

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $desc -Force | Out-Null

$info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "[DONE] Registered task: $TaskName" -ForegroundColor Green
Write-Host "  NextRunTime: $($info.NextRunTime)"
Write-Host "  DailyAt    : $DailyAt"
