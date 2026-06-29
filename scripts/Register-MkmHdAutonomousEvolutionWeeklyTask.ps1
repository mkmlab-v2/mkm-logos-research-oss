<#
.SYNOPSIS
  Register weekly Scheduled Task for HD autonomous evolution (B-track tier_0).

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Default: MKM_HdAutonomousEvolution_Weekly

.PARAMETER WeeklyAt
  Local time HH:mm for weekly Sunday trigger (default: 09:15 — after Bluesky probe 09:00).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_HdAutonomousEvolution_Weekly",
    [string]$WeeklyAt = "09:15"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/') } else { "C:\workspace" }
$runner = Join-Path $workspaceRoot "scripts\Invoke-MkmHdAutonomousEvolutionWeeklyRoutine_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $WeeklyAt -split ':'
if ($parts.Count -lt 2) {
    throw "WeeklyAt must be HH:mm (e.g. 09:15), got: $WeeklyAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`"" `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 120)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = @"
HD autonomous evolution weekly (tier_0): preflight + P0P1P2 hybrid + B-track intel + swarm accumulation + completion JSON.
[HYPO] research_only — no Track A / live trading. SSOT: docs/final/artifacts/mkm_high_dimensional_autonomous_evolution_v1_latest.json
"@.Trim()

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (weekly Sunday $WeeklyAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"
Write-Host "Verify: powershell -File scripts\Verify-MkmHdAutonomousEvolutionWeeklyScheduledTask_v1.ps1"
Write-Host "Manual: powershell -File scripts\Invoke-MkmHdAutonomousEvolutionWeeklyRoutine_v1.ps1"
