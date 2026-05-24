# R5: v3 EN vs KO gloss mean cosine (B-track ST index)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
py scripts/run_logos_rag_retrieval_v5_v3_bilingual_v1.py @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
