#Requires -Version 5.1
<#
.SYNOPSIS
  Register daily post-close KOSPI July scenario band tracker (3-axis flow observation) [HYPO].

.DESCRIPTION
  Runs Invoke-KospiJulyScenarioBandTrackerRoutine_v1.ps1 (pykrx net-buy fetch + rollup + tracker).
  observation_only · send_gate HOLD · not Track A / live trading.

  SSOT tier: docs/final/artifacts/mkm_scheduler_solo_core_stack_v1.json tier3_optional_active

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-KospiJulyScenarioBandTrackerTask_v1.ps1

.EXAMPLE
  powershell -File scripts\Register-KospiJulyScenarioBandTrackerTask_v1.ps1 -At "16:10" -SkipFlowFetch

.EXAMPLE
  powershell -File scripts\Register-KospiJulyScenarioBandTrackerTask_v1.ps1 -Remove
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM-Kospi-July-Scenario-Band-Tracker",
    [string]$At = "16:10",
    [switch]$SkipFlowFetch,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

$invokeScript = Join-Path $WorkspaceRoot "scripts\Invoke-KospiJulyScenarioBandTrackerRoutine_v1.ps1"
if (-not (Test-Path -LiteralPath $invokeScript)) {
    throw "Missing SSOT script: $invokeScript"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[REMOVED] $TaskName" -ForegroundColor Yellow
    exit 0
}

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$invokeScript`" -WorkspaceRoot `"$WorkspaceRoot`""
if ($SkipFlowFetch) {
    $argLine += " -SkipFlowFetch"
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 20) -MultipleInstances IgnoreNew -Hidden
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$desc = "Daily post-close KOSPI July scenario band tracker (3-axis flow; B-track [HYPO]; send_gate HOLD)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
    -Description $desc -Force | Out-Null

$i = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "[DONE] $TaskName at $At Next=$($i.NextRunTime)" -ForegroundColor Green
