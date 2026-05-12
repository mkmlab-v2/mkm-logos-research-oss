#Requires -Version 5.1
param(
    [string]$WorkspaceRoot = ""
)
$ErrorActionPreference = "Stop"
if (-not $WorkspaceRoot) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
& py (Join-Path $WorkspaceRoot "scripts/run_track_a_shadow_corpus_eval.py") --workspace-root $WorkspaceRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
