# B-track: export hanja lexicon + chunk compression hypo + wire AB (hypo lexicon).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

py scripts/export_ijeoma_hanja_codebook_lexicon_hypo_v1.py --source both --max-entries 12000
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/run_hanja_chunk_compression_hypo_eval_v1.py --max-cases 10
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/run_ijeoma_cjk_substitution_hypo_eval_v1.py --max-cases 10 --marker-strategy ascii_compact
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/apply_cjk_substitution_to_chunk_lane_v1.py --marker-strategy ascii_compact
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$lex = "reports/constitution/btrack_pilot/ijeoma_hanja_codebook_lexicon_v1_hypo_latest.json"
py scripts/run_universal_compression_bench_wire_ab_lane_v1.py --lane ijeoma_chunk --lexicon-json $lex --out reports/constitution/btrack_pilot/comp_universal_bench_matrix_wire_ab_ijeoma_chunk_hypo_lex_v1.json
exit $LASTEXITCODE
