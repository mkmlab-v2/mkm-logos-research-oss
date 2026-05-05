# Thin "Local" daily runner for scheduled task \Bitcoin-Ops-Phase1-Chain-Daily-Local
# (constitution + strict + Track A lane). Heavier options (showroom / OTel smoke) stay on
# \Bitcoin-Ops-Phase1-Chain-Daily only. Keep in sync with MKM-Ops-Phase1-Chain-Daily-V2 or stagger times to avoid double load.
param(
    [string]$TrackaDefaultLane = "c3_domain_gated"
)
$ErrorActionPreference = "Stop"
$chain = Join-Path $PSScriptRoot "run_ops_phase1_chain.ps1"
& $chain -IncludeConstitutionGates -Strict -TrackaDefaultLane $TrackaDefaultLane
exit $LASTEXITCODE
