<#
.SYNOPSIS
  Register scheduled task to build war-prolongation SITREP text.
#>
param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$TaskName = "MKM-War-Prolongation-SITREP-Daily",
  [string]$StartTime = "09:25"
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $WorkspaceRoot "scripts/build_war_prolongation_sitrep.py"
if (-not (Test-Path -LiteralPath $scriptPath)) {
  throw "Missing script: $scriptPath"
}

$args = "-WindowStyle Hidden -NoProfile -c `"py '$scriptPath'`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $args -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $StartTime
$settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -MultipleInstances IgnoreNew

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Description "Daily SITREP text build for war-prolongation benchmark." `
  -Force | Out-Null

Write-Host "OK: Scheduled SITREP task registered: $TaskName" -ForegroundColor Green
Write-Host "StartTime: $StartTime"

