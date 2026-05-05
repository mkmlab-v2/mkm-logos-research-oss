<#
.SYNOPSIS
  Register (or remove) a ~4-hour cadence Scheduled Task for the B-track evolution lightweight loop.

.DESCRIPTION
  Runs scripts/run_evolution_lightweight_loop_v1.py (move-threshold gate + per-lens scoreboard + HITL proposal).
  Six daily wall-clock triggers approximate a 4-hour cadence without replacing the heavy daily readiness job.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Evolution_Lightweight4h",
    [double]$KospiAbsRetThreshold = 0.012,
    [double]$BtcAbsRetThreshold = 0.025,
    [switch]$ForceEachRun,
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $WorkspaceRoot "scripts\run_evolution_lightweight_loop_v1.py"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$runnerArgs = @(
    $runner,
    "--kospi-abs-ret-threshold", "$KospiAbsRetThreshold",
    "--btc-abs-ret-threshold", "$BtcAbsRetThreshold"
)
if ($ForceEachRun) {
    $runnerArgs += "--force"
}
$argLine = $runnerArgs -join " "

$action = New-ScheduledTaskAction -Execute "py.exe" `
    -Argument $argLine `
    -WorkingDirectory $WorkspaceRoot

$base = Get-Date
$hours = @(0, 4, 8, 12, 16, 20)
$triggers = @()
foreach ($h in $hours) {
    $atToday = Get-Date -Year $base.Year -Month $base.Month -Day $base.Day -Hour $h -Minute 5 -Second 0
    $triggers += New-ScheduledTaskTrigger -Daily -At $atToday
}

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "B-track evolution lightweight loop: KOSPI/BTC last-bar move gate, prophecy_hit_rate_per_lens, lens_evolution_proposal (HITL-only)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $triggers `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (6x daily ~4h cadence, user=$env:USERNAME)"
Write-Host "Runner: $runner"
Write-Host "Argument: $argLine"
