<#
.SYNOPSIS
  Register or remove a daily scheduled task for compression bridge size gate.

.DESCRIPTION
  Runs scripts/run_compression_bridge_size_daily_gate_v1.ps1 once per day.
#>
param(
  [switch]$Remove,
  [string]$TaskName = "MKM_CompressionBridge_Size_Daily_Gate",
  [string]$WorkspaceRoot = "C:\workspace",
  [string]$At = "07:20"
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $WorkspaceRoot "scripts\run_compression_bridge_size_daily_gate_v1.ps1"

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
  -ExecutionTimeLimit (New-TimeSpan -Minutes 45)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "Daily compression bridge size gate (holdout + walkforward + promotion gate)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
  -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered: $TaskName (daily at $At)"
Write-Host "Runner: $runner"

