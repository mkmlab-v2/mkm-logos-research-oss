<#
.SYNOPSIS
  Register scheduled task for war-prolongation autopilot cycle.
#>
param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$TaskName = "MKM-War-Prolongation-Autopilot-Daily",
  [string]$StartTime = "09:05",
  [int]$MaxAttempts = 2,
  [int]$BackoffSeconds = 5
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $WorkspaceRoot "scripts/run_war_prolongation_autopilot_cycle.ps1"
if (-not (Test-Path -LiteralPath $scriptPath)) {
  throw "Missing script: $scriptPath"
}

$args = @(
  "-NoProfile",
  "-WindowStyle", "Hidden",
  "-ExecutionPolicy", "Bypass",
  "-File", "`"$scriptPath`"",
  "-WorkspaceRoot", "`"$WorkspaceRoot`"",
  "-MaxAttempts", "$MaxAttempts",
  "-BackoffSeconds", "$BackoffSeconds"
) -join " "

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
  -Description "Daily full autopilot cycle for war-prolongation benchmark (run+health+promotion flag)." `
  -Force | Out-Null

Write-Host "OK: Scheduled autopilot task registered: $TaskName" -ForegroundColor Green
Write-Host "StartTime: $StartTime"

