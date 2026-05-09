[CmdletBinding()]
param(
    [string]$TaskName = "MKM_ContextNote_ResearchGate_Daily",
    [string]$DailyAt = "06:40",
    [switch]$RunNow,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonExe = "py"
$runner = Join-Path $repoRoot "scripts\run_context_note_research_gate_v1.py"

if (-not (Test-Path $runner)) {
    throw "Missing runner script: $runner"
}

$taskCmd = "$pythonExe `"$runner`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -Command $taskCmd"
$trigger = New-ScheduledTaskTrigger -Daily -At $DailyAt
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

if ($Force) {
    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop | Out-Null
    } catch {
        # Ignore if missing.
    }
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Build context note profiles and run retrieval eval gate daily." `
    -Force | Out-Null

if ($RunNow) {
    Start-ScheduledTask -TaskName $TaskName
}

Write-Output "Registered task: $TaskName (daily at $DailyAt)"

