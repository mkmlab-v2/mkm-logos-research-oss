<#
.SYNOPSIS
  Register (or remove) MKM continuous daemon scheduled task.

.DESCRIPTION
  Runs scripts/run_mkm_continuous_daemon.ps1 at logon. Use this instead of one-shot poll scheduler
  when you want a single long-lived daemon loop.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_OrchestratorDaemon",
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$LoopSeconds = 300,
    [int]$MaxTasksPerInvocation = 4,
    [int]$HeavyEveryCycles = 12
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $WorkspaceRoot "scripts\run_mkm_continuous_daemon.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$argLine = "-NoProfile -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`" -LoopSeconds $LoopSeconds -MaxTasksPerInvocation $MaxTasksPerInvocation -HeavyEveryCycles $HeavyEveryCycles"

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "MKM continuous daemon loop (bridge merge + poll)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $description -Force | Out-Null
Write-Host "Registered scheduled task: $TaskName (logon, user=$env:USERNAME)"
Write-Host "Runner: $runner"
