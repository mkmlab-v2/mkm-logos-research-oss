<#
.SYNOPSIS
  AGCT pipeline integrity smoke: JSON race/format guards.

.DESCRIPTION
  Runs focused pytest regressions + tiny direct script runs for:
  - adversarial profile grid JSON integrity
  - stress-tail transition scan staged input snapshots
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

& py -m pytest "tests\test_agct_pipeline_integrity_smoke_v1.py" -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py "scripts\run_agct_adversarial_profile_grid_v1.py" `
    --weights-json "tmp\agct_sasang_axis_weights_active_btrack_v1.json" `
    --n-samples 120 `
    --seed 20260505 `
    --output-json "reports\agct_adversarial_profile_grid_v1_smoke_latest.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py "scripts\run_agct_stress_tail_transition_gate_scan_v1.py" `
    --sigmas 0.0315 `
    --trials 2 `
    --seed 20260505 `
    --base-weights-json "tmp\agct_sasang_axis_weights_active_btrack_v1.json" `
    --cohort-csv "tmp\bio_real_cohort_merged_with_sidecar_v1.csv" `
    --genotype-csv "tmp\bio_genotype_long_v1.csv" `
    --output-json "reports\agct_stress_tail_transition_gate_scan_v1_smoke_latest.json"
exit $LASTEXITCODE

