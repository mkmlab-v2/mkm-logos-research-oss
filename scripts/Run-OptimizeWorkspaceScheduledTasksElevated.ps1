# Re-runs optimize_workspace_scheduled_tasks.ps1 in an elevated PowerShell (UAC).
# Use when some tasks failed with "Access is denied" without admin rights.
$ErrorActionPreference = "Stop"
$script = Join-Path $PSScriptRoot "optimize_workspace_scheduled_tasks.ps1"
if (-not (Test-Path -LiteralPath $script)) {
    throw "Missing $script"
}
Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $script
) -Wait
