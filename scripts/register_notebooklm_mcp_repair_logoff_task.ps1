param(
    [switch]$Remove,
    [string]$TaskName = "MKM_RepairNotebookLmMcpStale_OnLogoff",
    [int]$StaleNodeMaxHours = 12
)

$ErrorActionPreference = "Stop"

$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\repair_notebooklm_mcp_auth_stuck.ps1"

if ($Remove) {
    schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$psArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$runner`" -StaleNodeMaxHours $StaleNodeMaxHours"
$taskRun = "cmd.exe /c cd /d `"$workspaceRoot`" && powershell.exe $psArgs"
$eventQuery = "*[System[Provider[@Name='Microsoft-Windows-Winlogon'] and (EventID=7002)]]"
schtasks /Create /TN $TaskName /TR $taskRun /SC ONEVENT /EC System /MO $eventQuery /RL LIMITED /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to register scheduled task via schtasks (exit=$LASTEXITCODE)"
}

Write-Host "Registered scheduled task: $TaskName (Winlogon EventID 7002 / logoff, user=$env:USERNAME)"
Write-Host "Runner: $runner"
Write-Host "StaleNodeMaxHours: $StaleNodeMaxHours"
