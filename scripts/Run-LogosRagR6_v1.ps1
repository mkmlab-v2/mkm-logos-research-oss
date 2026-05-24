# R6: bootstrap v3 bilingual + ko_only eval + pilot probes
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
py scripts/bootstrap_logos_semantic_query_set_v3_bilingual_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py scripts/run_logos_rag_retrieval_r6_v1.py @args
exit $LASTEXITCODE
