<#
.SYNOPSIS
  Register (or remove) a Scheduled Task that runs Telegram GO ingestion for MKM-Orchestrator.

.DESCRIPTION
  Polls Telegram getUpdates once per trigger and applies GO <task_id> via approve_mkm_orchestrator_task_v1.py.
  Offset: reports/mkm_orchestrator_telegram_offset.txt. Requires TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in .env.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_OrchestratorTelegramIngest",
    [int]$EveryMinutes = 2,
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\Invoke-MkmOrchestratorTelegramIngest.ps1"

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
    -ExecutionTimeLimit ([TimeSpan]::FromMinutes(5))

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "MKM-Orchestrator Telegram ingest (GO commands); offset reports/mkm_orchestrator_telegram_offset.txt"

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (every $EveryMinutes min)"
Write-Host "Runner: $runner"
