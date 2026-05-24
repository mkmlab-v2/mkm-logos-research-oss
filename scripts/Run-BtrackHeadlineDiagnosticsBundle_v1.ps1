#Requires -Version 5.1
<#
.SYNOPSIS
  B-track headline diagnostics: miss report + margin/weight sweep (research only).
#>
param([string]$WorkspaceRoot = "C:\workspace")

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

& py scripts\build_btrack_headline_miss_report_v1.py
if ($LASTEXITCODE -ne 0) { throw "miss report exit $LASTEXITCODE" }

& py scripts\run_btrack_v1_headline_tune_sweep_v1.py
if ($LASTEXITCODE -ne 0) { throw "headline tune sweep exit $LASTEXITCODE" }

& py scripts\build_btrack_wrong_direction_lens_report_v1.py
if ($LASTEXITCODE -ne 0) { throw "wrong-direction lens report exit $LASTEXITCODE" }

& py scripts\run_btrack_price_lens_bear_calibration_sweep_v1.py
if ($LASTEXITCODE -ne 0) { throw "price lens bear calibration sweep exit $LASTEXITCODE" }

& py scripts\build_btrack_wrong_dir_counterfactual_matrix_v1.py
if ($LASTEXITCODE -ne 0) { throw "wrong-dir counterfactual matrix exit $LASTEXITCODE" }

& py scripts\run_btrack_wrong_dir_sign_inversion_experiment_v1.py
if ($LASTEXITCODE -ne 0) { throw "wrong-dir sign inversion experiment exit $LASTEXITCODE" }

& py scripts\run_btrack_conditional_bear_override_experiment_v1.py
if ($LASTEXITCODE -ne 0) { throw "conditional bear override experiment exit $LASTEXITCODE" }

Write-Host "[OK] Headline diagnostics complete" -ForegroundColor Green
