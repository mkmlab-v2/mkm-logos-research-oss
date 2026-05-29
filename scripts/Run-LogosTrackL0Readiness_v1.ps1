# Track L L0 readiness (verse resolver + corpus smoke).
param(
    [string]$WorkspaceRoot = $(if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT } else { (Resolve-Path (Join-Path $PSScriptRoot '..')).Path })
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $WorkspaceRoot
try {
    & py -3 scripts/run_logos_track_l_l0_readiness_v1.py @args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
