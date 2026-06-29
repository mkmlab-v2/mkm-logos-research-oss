# PersonaDiary Lovable-equivalent DoD bundle (tier_0 default).
param(
    [switch]$IncludeVisionQa,
    [ValidateSet('dry-run', 'developer', 'vertex', 'azure')]
    [string]$Billing = 'dry-run',
    [switch]$SkipAndroid,
    [switch]$StrictPlanned,
    [switch]$StrictVision
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$argsList = @('scripts/run_personadiary_lovable_dod_bundle_v1.py')
if ($IncludeVisionQa) { $argsList += '--include-vision-qa'; $argsList += '--billing'; $argsList += $Billing }
if ($SkipAndroid) { $argsList += '--skip-android' }
if ($StrictPlanned) { $argsList += '--strict-planned' }
if ($StrictVision) { $argsList += '--strict-vision' }

& py @argsList
exit $LASTEXITCODE
