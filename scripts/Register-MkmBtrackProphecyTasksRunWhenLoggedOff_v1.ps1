#Requires -Version 5.1
<#
.SYNOPSIS
  Re-register MKM B-track / prophecy scheduled tasks with -RunWhenLoggedOff (S4U).

.DESCRIPTION
  Must run in an elevated PowerShell (Administrator). Without admin, Windows returns
  Access denied for Register-ScheduledTask when switching to S4U.

  Does NOT modify schtasks-based GeneralProphecy tasks; see NOTES.

.EXAMPLE
  # Right-click PowerShell -> Run as administrator, then:
  Set-Location C:\workspace
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Register-MkmBtrackProphecyTasksRunWhenLoggedOff_v1.ps1

.NOTES
  GeneralProphecyDailyQueueV1 / GeneralProphecyHoldoutEvolutionWeeklyV1 use schtasks.exe.
  For "run whether user is logged on or not", use Task Scheduler GUI on those two tasks
  or recreate them with stored credentials (schtasks /RU /RP) — not automated here.
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

$isAdmin = ([Security.Principal.WindowsPrincipal] (
    New-Object Security.Principal.WindowsPrincipal ([Security.Principal.WindowsIdentity]::GetCurrent())
)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[FAIL] Run this script from an elevated PowerShell (Run as administrator)." -ForegroundColor Red
    Write-Host "  cd $root"
    Write-Host "  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Register-MkmBtrackProphecyTasksRunWhenLoggedOff_v1.ps1"
    exit 2
}

Write-Host "[OK] Elevated shell detected. Re-registering tasks with -RunWhenLoggedOff ..." -ForegroundColor Green

& (Join-Path $root "scripts\Register-BtrackAutomationHealthTask.ps1") -RunWhenLoggedOff
& (Join-Path $root "scripts\Register-BTrackDailyHypothesisTask.ps1") -At "08:35" -ResearchEvaluationInstrument btc -SkipPanel24hAlertsCheck -SkipProphecyContemplationGemini -RunWhenLoggedOff
& (Join-Path $root "scripts\Register-ProphecyPanel24hAlertsTask.ps1") -At "09:05" -RunWhenLoggedOff
& (Join-Path $root "scripts\Register-ProphecyEvolutionWatchdogTask.ps1") -At "10:15" -RunWhenLoggedOff
& (Join-Path $root "scripts\Register-BtcWeightHitRateBundleWeeklyTask.ps1") -SundayAt "09:15" -RunWhenLoggedOff

Write-Host ""
Write-Host "[NEXT] Verify LogonType (expect S4U for cmdlet-registered tasks):" -ForegroundColor Cyan
Get-ScheduledTask -TaskName @(
    "MKM_BTrack_Automation_Health_Daily",
    "MKM-BTrack-DailyHypothesis-Chain",
    "MKM-Prophecy-Panel-24h-Alerts",
    "MKM-Prophecy-Evolution-Watchdog",
    "MKM-BTrack-BtcWeight-HitRateBundle-Weekly"
) -ErrorAction SilentlyContinue | ForEach-Object {
    "{0}  LogonType={1}" -f $_.TaskName, $_.Principal.LogonType
}

Write-Host ""
Write-Host "[NOTE] schtasks tasks (manual if needed): \GeneralProphecyDailyQueueV1 , \GeneralProphecyHoldoutEvolutionWeeklyV1" -ForegroundColor Yellow
Write-Host "[DONE] Register-MkmBtrackProphecyTasksRunWhenLoggedOff_v1.ps1" -ForegroundColor Green
