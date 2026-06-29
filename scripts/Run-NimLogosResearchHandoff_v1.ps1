# NVIDIA NIM 70B — Logos B-track handoff (no codec wire)
param(
    [switch] $SkipEmbed,
    [int] $MaxTokens = 900
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$args = @('scripts/run_nim_logos_research_handoff_v1.py', '--max-tokens', "$MaxTokens")
if ($SkipEmbed) { $args += '--skip-embed' }
& py @args
exit $LASTEXITCODE
