# Trust Composition glass/blur commander visual A/B + clinic LOI Figma pack.
param(
    [ValidateSet('prefer_flat_baseline', 'glass_ok_hub_only', 'fail')]
    [string]$Verdict = 'prefer_flat_baseline',
    [switch]$SkipPytest,
    [switch]$SkipFigmaPack
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

$args = @('scripts/run_trust_composition_glass_blur_commander_visual_chain_v1.py', '--verdict', $Verdict)
if ($SkipPytest) { $args += '--skip-pytest' }
if ($SkipFigmaPack) { $args += '--skip-figma-pack' }

& py @args
exit $LASTEXITCODE
