# After CLOUDFLARE_API_TOKEN has Zone Settings Edit: probe -> finalize -> site readiness.
param(
    [switch]$SkipProbe,
    [switch]$SkipSiteProbe
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $SkipProbe) {
    py scripts/probe_mkmlab_cloudflare_dns_token_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

py scripts/finalize_mkmlab_cloudflare_zone_v1.py --polls 2 --sleep-s 5
$fin = $LASTEXITCODE
if ($fin -ne 0) { exit $fin }

if (-not $SkipSiteProbe) {
    py scripts/probe_mkmlab_space_readiness_v1.py
    exit $LASTEXITCODE
}
exit 0
