<#
.SYNOPSIS
  Myeongni package_b chain smoke (both/balanced/attack) + pytest guard.

.DESCRIPTION
  Runs the one-click chain script in all modes and executes focused regression tests.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

& py (Join-Path $WorkspaceRoot "scripts\run_myeongni_package_b_chain_v1.py") --mode both
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py (Join-Path $WorkspaceRoot "scripts\run_myeongni_package_b_chain_v1.py") --mode balanced
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py (Join-Path $WorkspaceRoot "scripts\run_myeongni_package_b_chain_v1.py") --mode attack
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py -m pytest `
    "tests\test_run_myeongni_package_b_chain_v1.py" `
    "tests\test_build_mkm_myeongni_response_v2.py" -q
exit $LASTEXITCODE
