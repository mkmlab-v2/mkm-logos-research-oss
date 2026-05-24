#Requires -Version 5.1
<#
.SYNOPSIS
  personadiary.com Email Routing setup wrapper.

.DESCRIPTION
  Wraps setup_cloudflare_email_routing_v1.py with personadiary defaults.
  Use this after updating CLOUDFLARE_API_TOKEN with Email Routing scopes.

  Default route:
    hello@personadiary.com -> support@mkmlife.com

.PARAMETER LocalPart
  Local mailbox part for personadiary.com (default: hello)

.PARAMETER ForwardTo
  Destination inbox (default: support@mkmlife.com)

.PARAMETER ZoneId
  Optional explicit zone id override.

.PARAMETER UseFixtureZoneId
  Use scripts/data/hostinger_full_exit/personadiary_cloudflare_zone_v1.json zone_id.

.PARAMETER DryRun
  Read-only probe (no mutation).
#>
param(
    [string]$LocalPart = "hello",
    [string]$ForwardTo = "support@mkmlife.com",
    [string]$ZoneId = "",
    [switch]$UseFixtureZoneId = $true,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..\")).Path
$py = Join-Path $PSScriptRoot "setup_cloudflare_email_routing_v1.py"
if (-not (Test-Path -LiteralPath $py)) { throw "Missing script: $py" }

if ($UseFixtureZoneId -and [string]::IsNullOrWhiteSpace($ZoneId)) {
    $fixturePath = Join-Path $PSScriptRoot "data\hostinger_full_exit\personadiary_cloudflare_zone_v1.json"
    if (-not (Test-Path -LiteralPath $fixturePath)) { throw "Missing fixture: $fixturePath" }
    $fixture = Get-Content -LiteralPath $fixturePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([string]::IsNullOrWhiteSpace($fixture.zone_id)) {
        throw "fixture.zone_id empty in $fixturePath"
    }
    $ZoneId = [string]$fixture.zone_id
}

$argsList = @(
    $py,
    "--apex", "personadiary.com",
    "--local-part", $LocalPart.Trim(),
    "--forward-to", $ForwardTo.Trim()
)
if (-not [string]::IsNullOrWhiteSpace($ZoneId)) {
    $argsList += @("--zone-id", $ZoneId.Trim())
}
if ($DryRun) {
    $argsList += "--dry-run"
}

& py @argsList
exit $LASTEXITCODE

