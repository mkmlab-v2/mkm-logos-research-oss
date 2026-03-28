# P0 Step 4: scoped pytest bundle (prophecy / dual-regime alignment).
# SSOT: docs/final/P0_COMMERCIALIZATION_TRACKER.md — use `py` only (not `python`).
# Do not run full-repo pytest from here; keep the file list explicit.

$ErrorActionPreference = 'Stop'

$btRoot = (Get-Item -LiteralPath $PSScriptRoot).Parent.Parent.Parent.FullName
Set-Location -LiteralPath $btRoot

# Fact-Lock SSOT: dual-regime smoke (13 cases). CI: .github/workflows/dual-regime-integrity.yml
$testFiles = @(
    'tests/test_dual_regime_api_smoke.py'
)

$args = @('-m', 'pytest') + ($testFiles | ForEach-Object { $_ }) + @('-v', '--tb=short')
& py @args
exit $LASTEXITCODE
