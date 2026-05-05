<#
.SYNOPSIS
  Create docs/final/artifacts/todo_queue_latest.json from a template if missing.

.DESCRIPTION
  -Profile Example: full sample (noop + daily readiness + HITL placeholder).
  -Profile SmokeFirst: single fast PowerShell noop — safest first non-dry-run poll on Windows.
  -Profile SmokeFirstPython: single Python noop — Linux/macOS or PS-less hosts.
  -Profile TrackCFromBridge: run apply_trackc_plan_bridge_to_queue_v1.py (Track C business plan bridge JSON → todo_queue_latest.json).
  Use -Force to overwrite.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [ValidateSet("Example", "SmokeFirst", "SmokeFirstPython", "TrackCFromBridge")]
    [string]$Profile = "Example",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$dst = Join-Path $WorkspaceRoot "docs\final\artifacts\todo_queue_latest.json"

if ($Profile -eq "TrackCFromBridge") {
    if ((Test-Path -LiteralPath $dst) -and -not $Force) {
        Write-Host "Already exists (skip): $dst"
        Write-Host "Use -Force to regenerate from mkm_trackc_plan_orchestrator_bridge_v1.json"
        exit 0
    }
    $apply = Join-Path $WorkspaceRoot "scripts\apply_trackc_plan_bridge_to_queue_v1.py"
    if (-not (Test-Path -LiteralPath $apply)) { throw "Not found: $apply" }
    & py $apply --workspace-root $WorkspaceRoot
    exit $LASTEXITCODE
}

$name = switch ($Profile) {
    "SmokeFirst" { "todo_queue_smoke_first_v1.json" }
    "SmokeFirstPython" { "todo_queue_smoke_first_python_v1.json" }
    default { "todo_queue_example_v1.json" }
}
$src = Join-Path $WorkspaceRoot "docs\final\artifacts\$name"

if (-not (Test-Path -LiteralPath $src)) {
    throw "Source not found: $src"
}

if ((Test-Path -LiteralPath $dst) -and -not $Force) {
    Write-Host "Already exists (skip): $dst"
    Write-Host "Use -Force to overwrite from example."
    exit 0
}

Copy-Item -LiteralPath $src -Destination $dst -Force
Write-Host "OK: $dst (from $name, Profile=$Profile)"
