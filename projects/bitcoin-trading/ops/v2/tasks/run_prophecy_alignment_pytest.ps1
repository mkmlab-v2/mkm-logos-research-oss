# P0 Step 4: scoped pytest bundle (prophecy / dual-regime alignment).
# SSOT: docs/final/P0_COMMERCIALIZATION_TRACKER.md — use `py` only (not `python`).
# Do not run full-repo pytest from here; keep the file list explicit.

$ErrorActionPreference = 'Stop'

$btRoot = (Get-Item -LiteralPath $PSScriptRoot).Parent.Parent.Parent.FullName
$workspaceRoot = (Get-Item -LiteralPath $btRoot).Parent.FullName

# Fact-Lock SSOT: dual-regime smoke (13 cases). CI: .github/workflows/dual-regime-integrity.yml
Set-Location -LiteralPath $btRoot
& py -m pytest 'tests/test_dual_regime_api_smoke.py' -v --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Workspace-root Fact-Lock (logos snapshot + CROSS_REF join); mirrors CI steps after prophecy bundle.
Set-Location -LiteralPath $workspaceRoot
& py -m pytest `
    'tests/test_logos_state_mapping_v1_snapshot.py' `
    'tests/test_cross_ref_dss_schema.py' `
    -q --tb=short
exit $LASTEXITCODE
