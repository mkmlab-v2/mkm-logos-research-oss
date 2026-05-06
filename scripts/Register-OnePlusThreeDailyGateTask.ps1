<#
.SYNOPSIS
  Register or remove a daily scheduled task for the 1+3 warning/critical gate.

.DESCRIPTION
  Runs scripts/run_one_plus_three_daily_gate_v1.ps1 once per day.
#>
param(
  [switch]$Remove,
  [string]$TaskName = "MKM_OnePlusThree_Daily_Gate",
  [string]$WorkspaceRoot = "C:\workspace",
  [string]$At = "07:30"
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $WorkspaceRoot "scripts\run_one_plus_three_daily_gate_v1.ps1"

if ($Remove) {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
  Write-Host "Removed scheduled task (if existed): $TaskName"
  exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
  throw "Runner not found: $runner"
}

$atTime = [DateTime]::ParseExact($At, "HH:mm", $null)
$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $atTime
$settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "Daily 1+3 threshold gate (7d/14d + warning/critical)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
  -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered: $TaskName (daily at $At)"
Write-Host "Runner: $runner"
