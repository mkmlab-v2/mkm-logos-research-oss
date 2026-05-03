<#
.SYNOPSIS
  Register (or remove) daily Scheduled Task for Vibe B-Track prophecy-evolution loop.

.DESCRIPTION
  Executes scripts/run_vibe_daily_prophecy_evolution_loop_v1.ps1 once per day.
  Scope is research-only and does not auto-apply strategy changes.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "VibeDailyProphecyEvolutionLoop",
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$RunsPerPrompt = 10,
    [switch]$StrictCoverageGate,
    [string]$At = "01:20"
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $WorkspaceRoot "scripts\Launch-VibeDailyProphecyEvolutionLoop.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$time = [DateTime]::ParseExact($At, "HH:mm", $null)
$argument = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -RunsPerPrompt $RunsPerPrompt"
if ($StrictCoverageGate) {
    $argument += " -StrictCoverageGate"
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "Daily Vibe B-Track prophecy-evolution loop (research-only)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $description -Force | Out-Null
Write-Host "Registered scheduled task: $TaskName (daily at $At, user=$env:USERNAME)"
Write-Host "Runner: $runner"
