<#
.SYNOPSIS
  Register scheduled health-check task for war benchmark automation.
#>
param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$TaskName = "MKM-War-Prolongation-Benchmark-Health-Daily",
  [string]$StartTime = "09:20",
  [string]$MonitoredTaskName = "MKM-War-Prolongation-Autopilot-Daily"
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $WorkspaceRoot "scripts/check_war_prolongation_benchmark_health.ps1"
if (-not (Test-Path -LiteralPath $scriptPath)) {
  throw "Missing script: $scriptPath"
}

$args = @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-File", "`"$scriptPath`"",
  "-WorkspaceRoot", "`"$WorkspaceRoot`"",
  "-TaskName", "`"$MonitoredTaskName`""
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
  -Description "Daily health check for war-prolongation benchmark automation." `
  -Force | Out-Null

Write-Host "OK: Scheduled health task registered: $TaskName" -ForegroundColor Green
Write-Host "StartTime: $StartTime"

