<#
.SYNOPSIS
  Register (or remove) a Scheduled Task that runs mkm_orchestrator_poll.ps1 periodically.

.DESCRIPTION
  Bounded automation poll; queue: docs/final/artifacts/todo_queue_latest.json.
  Adjust interval via -EveryMinutes. Execution limit generous for long readiness chains.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_OrchestratorPoll",
    [int]$EveryMinutes = 5,
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\mkm_orchestrator_poll.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

if ($EveryMinutes -lt 1 -or $EveryMinutes -gt 1440) {
    throw "EveryMinutes must be 1..1440"
}

$argument = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument -WorkingDirectory $WorkspaceRoot

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes $EveryMinutes) -RepetitionDuration (New-TimeSpan -Days 3652)

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "MKM-Orchestrator poll (todo_queue_v1); audit reports/mkm_orchestrator_audit.jsonl"

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (every $EveryMinutes min, user=$env:USERNAME)"
Write-Host "Runner: $runner"
