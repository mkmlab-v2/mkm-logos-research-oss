<#
.SYNOPSIS
  Register (or remove) scheduled task for mode-router v3 canary guard.

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Scheduled task name.

.PARAMETER IntervalMinutes
  Monitor interval in minutes (default: 30).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_L1InverseDecoder_ModeRouterV3_CanaryGuard",
    [int]$IntervalMinutes = 30,
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$Phase = "phase_1",
    [int]$TrafficPct = 10,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if ($IntervalMinutes -lt 5) {
    throw "IntervalMinutes must be >= 5."
}

$runner = Join-Path $WorkspaceRoot "scripts\run_l1_inverse_decoder_mode_router_v3_canary_guard.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Guard runner not found: $runner"
}

$dryRunArg = ""
if ($DryRun) {
    $dryRunArg = " -DryRun"
}

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`" -Phase `"$Phase`" -TrafficPct $TrafficPct$dryRunArg"

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Mode-router v3 canary monitor and automatic rollback switch guard."
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (every $IntervalMinutes minutes, user=$env:USERNAME, phase=$Phase, traffic=$TrafficPct%)"
Write-Host "Runner: $runner"
