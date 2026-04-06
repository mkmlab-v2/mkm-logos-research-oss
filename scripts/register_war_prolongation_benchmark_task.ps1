<#
.SYNOPSIS
  Register a scheduled task for resilient war-prolongation benchmark runs.

.DESCRIPTION
  Creates/updates a daily Windows Scheduled Task that executes:
    scripts/run_war_prolongation_benchmark_resilient.ps1
#>
param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$TaskName = "MKM-War-Prolongation-Benchmark-Daily",
  [string]$StartTime = "09:10",
  [int]$MaxAttempts = 3,
  [int]$BackoffSeconds = 20
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $WorkspaceRoot "scripts/run_war_prolongation_benchmark_resilient.ps1"
if (-not (Test-Path -LiteralPath $scriptPath)) {
  throw "Missing script: $scriptPath"
}

$actionArgs = @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-File", "`"$scriptPath`"",
  "-WorkspaceRoot", "`"$WorkspaceRoot`"",
  "-MaxAttempts", "$MaxAttempts",
  "-BackoffSeconds", "$BackoffSeconds"
) -join " "

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $actionArgs -WorkingDirectory $WorkspaceRoot
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
  -Description "Resilient daily war-prolongation benchmark chain (observation lane)." `
  -Force | Out-Null

Write-Host "OK: Scheduled task registered: $TaskName" -ForegroundColor Green
Write-Host "StartTime: $StartTime"
Write-Host "Command: powershell.exe $actionArgs"

