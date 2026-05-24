# Thematic precision v7: pack refresh → export 7 provisional → precision gold → eval → gate
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

py scripts/bootstrap_logos_query_gold_human_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/export_logos_rag_provisional_thematic_review_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/apply_logos_rag_thematic_precision_v7_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/run_logos_rag_dual_gold_eval_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/check_logos_rag_btrack_promotion_gate_v1.py --run-pytest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/build_logos_rag_promotion_review_packet_v1.py
exit $LASTEXITCODE
