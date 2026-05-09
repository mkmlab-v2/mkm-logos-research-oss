<#
.SYNOPSIS
  Strict monitor chain for AGCT Sasang Stage2 operations.
  Runs strict-equivalent baseline chain and verifies stage2 gates.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

& py "scripts\run_agct_sigma_locked_baseline_chain_v1.py" `
  --repro-trials 5 `
  --repro-batches 1 `
  --h2h-trials 5 `
  --h2h-batches 1 `
  --daily-drift-runs 2 `
  --run-regression-check `
  --strict-regression-check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py "scripts\build_agct_sasang_stage2_candidate_compare_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py "scripts\append_agct_sasang_stage2_compare_history_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py "scripts\check_agct_sasang_stage2_promotion_gate_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py "scripts\check_agct_sasang_stage2_fasttrack_gate_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py "scripts\check_agct_sasang_stage2_d7_checkpoint_v1.py"
exit $LASTEXITCODE
