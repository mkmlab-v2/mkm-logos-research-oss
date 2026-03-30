# Register (or remove) a Windows Scheduled Task for state execution packet cycles.
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_State_Execution_Packet_Cycle",
    [int]$EveryMinutes = 30
)

$ErrorActionPreference = "Stop"

$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_state_execution_packet_cycle.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}
if ($EveryMinutes -lt 5) {
    throw "EveryMinutes must be >= 5"
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runner`"" `
    -WorkingDirectory $workspaceRoot

# Use schtasks for minute-based repetition compatibility across PowerShell versions.
$startTime = (Get-Date).AddMinutes(1).ToString("HH:mm")
$taskRun = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$runner`""

schtasks /Create `
    /TN $TaskName `
    /TR $taskRun `
    /SC MINUTE `
    /MO $EveryMinutes `
    /ST $startTime `
    /F | Out-Null

Write-Host "Registered scheduled task: $TaskName"
Write-Host "Runner: $runner"
Write-Host "Interval: every ${EveryMinutes} minutes"
