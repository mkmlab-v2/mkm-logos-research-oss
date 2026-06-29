#Requires -Version 5.1
<#
.SYNOPSIS
  Offline web_ops_regime health smoke: pytest + gate check + health summary.
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

& py -m pytest tests/test_web_ops_regime_gate_v1.py -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py (Join-Path $root "scripts\run_web_ops_regime_full_bundle_v1.py") `
    --skip-live-cdp `
    --no-seed-baselines `
    --require-dual-alignment `
    --fail-on-pointer-drift
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py (Join-Path $root "scripts\build_web_ops_regime_health_summary_v1.py") --require-health-ok
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py (Join-Path $root "scripts\build_mkm_ops_memory_web_ops_overlay_v1.py")
exit $LASTEXITCODE
