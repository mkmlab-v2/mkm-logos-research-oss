# Poll data/wtt/intake for new customer JSONL -> auto intake (no synthetic/stub).
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$DryRun,
    [string]$ForceJsonl = "",
    [switch]$RegisterTask,
    [switch]$UnregisterTask
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

if ($RegisterTask) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-WttPilotIntakeDropWatchTask.ps1 -WorkspaceRoot $WorkspaceRoot
    exit $LASTEXITCODE
}
if ($UnregisterTask) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-WttPilotIntakeDropWatchTask.ps1 -WorkspaceRoot $WorkspaceRoot -Remove
    exit $LASTEXITCODE
}

Write-Host "=== WTT intake drop watch (poll once) ===" -ForegroundColor Cyan
Write-Host "dir: data/wtt/intake | SEND_GATE HOLD | customer_provided required" -ForegroundColor Yellow

$argsPy = @("scripts/watch_wtt_pilot_intake_drop_v1.py")
if ($DryRun) { $argsPy += "--dry-run" }
if ($ForceJsonl -ne "") { $argsPy += @("--force-jsonl", $ForceJsonl) }

& py @argsPy
exit $LASTEXITCODE
