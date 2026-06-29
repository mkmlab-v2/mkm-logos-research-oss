# NVIDIA API primary — Nemotron inference via NIM (no WSL 30B train)
param([int] $MaxTokens = 500)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
& py scripts/run_nvidia_api_primary_lane_v1.py --max-tokens $MaxTokens
exit $LASTEXITCODE
