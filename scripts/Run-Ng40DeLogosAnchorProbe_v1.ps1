# [HYPO] NG-40 Logos anchor probe via Discovery Engine (human review before LUT).
param(
    [switch]$DryRun,
    [int]$PageSize = 5
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$argsList = @('scripts/run_ng40_de_logos_anchor_probe_v1.py', '--page-size', "$PageSize")
if ($DryRun) {
    $argsList += '--dry-run'
}

& py @argsList
exit $LASTEXITCODE
