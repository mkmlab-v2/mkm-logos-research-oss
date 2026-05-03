<#
.SYNOPSIS
  Local smoke: pytest orchestrator tests + poll dry-run (example queue).

.DESCRIPTION
  No Telegram credentials required. Run from repo root or pass -WorkspaceRoot.
  Installs jsonschema (quiet) so tests/test_apply_trackc_plan_bridge_v1.py is not skipped.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipJsonSchemaPip
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

& py (Join-Path $WorkspaceRoot "scripts\verify_mkm_orchestrator_bundle_v1.py") --workspace-root $WorkspaceRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipJsonSchemaPip) {
    & py -m pip install -q jsonschema
}

& py -m pytest `
    "tests\test_mkm_orchestrator_queue_v1.py" `
    "tests\test_mkm_orchestrator_telegram_v1.py" `
    "tests\test_mkm_orchestrator_poll_smoke_v1.py" `
    "tests\test_mkm_orchestrator_bundle_verify_v1.py" `
    "tests\test_apply_trackc_plan_bridge_v1.py" -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py (Join-Path $WorkspaceRoot "scripts\mkm_orchestrator_poll_v1.py") `
    "--workspace-root" $WorkspaceRoot `
    "--queue" (Join-Path $WorkspaceRoot "docs\final\artifacts\todo_queue_example_v1.json") `
    "--dry-run" "--skip-lock"
exit $LASTEXITCODE
