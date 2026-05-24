# B-track billing lane: o200k_tight markers on disk (does not change hook default ascii_compact).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

$lane = "docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_cjk_o200k_tight_v1.json"
$sweep = "reports/constitution/btrack_pilot/comp_universal_bench_matrix_sweep_ijeoma_chunk_cjk_o200k_tight_v1.json"

py scripts/apply_cjk_substitution_to_chunk_lane_v1.py --marker-strategy o200k_tight --out-lane $lane
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/run_universal_compression_bench_matrix_sweep_v1.py --input $lane --out-json $sweep --eval-mode baseline
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/build_ijeoma_cjk_o200k_diagnosis_v1.py --marker-strategy o200k_tight --lane-json $lane --out-json reports/constitution/btrack_pilot/comp_ijeoma_cjk_o200k_diagnosis_o200k_tight_v1.json
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/build_ijeoma_cjk_hypo_bundle_summary_v1.py
exit $LASTEXITCODE
