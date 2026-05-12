#Requires -Version 5.1
param([string]$WorkspaceRoot = "")
$ErrorActionPreference = "Stop"
if (-not $WorkspaceRoot) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
& py (Join-Path $WorkspaceRoot "scripts/run_track_a_metering_summary.py") --workspace-root $WorkspaceRoot
exit $LASTEXITCODE
