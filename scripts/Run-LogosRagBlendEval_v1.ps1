# [HYPO] Blend thematic eval — separate gold file; operational SSOT untouched
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
py scripts/run_logos_rag_blend_eval_v1.py
exit $LASTEXITCODE
