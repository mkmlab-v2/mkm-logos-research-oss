# P15 R6 ko_only lane: signoff (if needed) → dual eval → 12 pilots → gate
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

py scripts/run_logos_rag_r6_ko_only_lane_v1.py @args
exit $LASTEXITCODE
