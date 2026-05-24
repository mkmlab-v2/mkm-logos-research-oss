# L2 post-R6: adjudication pack → dual-track signoff → merge/bridge → gate
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

py scripts/bootstrap_logos_query_gold_human_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/apply_logos_rag_commander_gold_signoff_v1.py --l2-provisional-thematic pack_ranks_2_4
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/run_logos_rag_dual_gold_eval_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/merge_logos_rag_pilot_ko_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$merged = 'reports/constitution/btrack_pilot/philosophy_lane_rag_pilot_r6_merged_q01_q12_ko_only_latest.json'
if (-not (Test-Path $merged)) {
  $merged = 'reports/constitution/btrack_pilot/philosophy_lane_rag_pilot_r4_merged_q01_q12_ko_latest.json'
}

py scripts/build_semantic_rag_bridge_insight_bundle_v1.py --philosophy-pilot-json $merged --calibration-kind none
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/run_logos_rag_hybrid_improvement_sweep_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/check_logos_rag_btrack_promotion_gate_v1.py --run-pytest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/build_logos_rag_promotion_review_packet_v1.py
exit $LASTEXITCODE
