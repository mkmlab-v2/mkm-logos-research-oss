# M0→M3 compression hardening milestone chain (parallel inner steps)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
py scripts/run_compression_hardening_milestone_chain_v1.py --skip-bench-smoke --skip-demo @args
exit $LASTEXITCODE
