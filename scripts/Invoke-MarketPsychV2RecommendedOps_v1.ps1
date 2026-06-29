# B-track market rail recommended ops (dna=0, market=1) — [HYPO] research_only
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
py scripts/run_market_psych_v2_recommended_ops_v1.py @args
exit $LASTEXITCODE
