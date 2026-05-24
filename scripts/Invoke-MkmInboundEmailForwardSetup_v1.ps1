#Requires -Version 5.1
<#
.SYNOPSIS
  Forward support@mkmlife.com and admin@no1kmedi.com to one verified inbox (default: MKM_MKMLIFE_SUPPORT_FORWARD_TO).

.DESCRIPTION
  Wraps setup_cloudflare_email_routing_v1.py twice (mkmlife + no1kmedi apex).
  Destination must be verified once in Cloudflare Email Routing (e.g. moksorinw@gmail.com).

  Prerequisite: apex MX uses Cloudflare Email Routing (not Hostinger/Google-only MX on the same apex).
  If admin@no1kmedi.com MX points to Google Workspace only, use Workspace forwarding instead.

.PARAMETER ForwardTo
  Verified destination inbox. Default: env MKM_MKMLIFE_SUPPORT_FORWARD_TO, else moksorinw@gmail.com.

.PARAMETER DryRun
  Zone/routing read only (no mutations).

.NOTES
  API token: Zone Email Routing Rules Edit + Account Email Routing Addresses Edit (DNS-only token → 403).
  Reports overwrite reports/cloudflare_email_routing_setup_latest.json (last run wins).
#>
param(
    [string]$ForwardTo = "",
    [switch]$DryRun,
    [string]$MkmlifeZoneId = "",
    [string]$No1kmediZoneId = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

if ([string]::IsNullOrWhiteSpace($ForwardTo)) {
    $ForwardTo = [Environment]::GetEnvironmentVariable("MKM_MKMLIFE_SUPPORT_FORWARD_TO", "Process")
    if ([string]::IsNullOrWhiteSpace($ForwardTo)) {
        $ForwardTo = [Environment]::GetEnvironmentVariable("MKM_MKMLIFE_SUPPORT_FORWARD_TO", "User")
    }
    if ([string]::IsNullOrWhiteSpace($ForwardTo)) {
        $ForwardTo = "moksorinw@gmail.com"
    }
}
$ForwardTo = $ForwardTo.Trim()

$wrapper = Join-Path $PSScriptRoot "Invoke-CloudflareEmailRoutingSetup_v1.ps1"
if (-not (Test-Path -LiteralPath $wrapper)) {
    throw "Missing $wrapper"
}

$routes = @(
    @{ Apex = "mkmlife.com"; LocalPart = "support"; ZoneId = $MkmlifeZoneId; UseFixture = $true }
    @{ Apex = "no1kmedi.com"; LocalPart = "admin"; ZoneId = $No1kmediZoneId; UseFixture = $true }
)

$worst = 0
foreach ($r in $routes) {
    Write-Host "== $($r.LocalPart)@$($r.Apex) -> $ForwardTo ==" -ForegroundColor Cyan
    $argsList = @(
        "-Apex", $r.Apex,
        "-LocalPart", $r.LocalPart,
        "-ForwardTo", $ForwardTo
    )
    if (-not [string]::IsNullOrWhiteSpace($r.ZoneId)) {
        $argsList += @("-ZoneId", $r.ZoneId.Trim())
    }
    elseif ($r.UseFixture -and $r.Apex -eq "mkmlife.com") {
        $argsList += "-UseMkmlifeFixtureZoneId"
    }
    elseif ($r.UseFixture -and $r.Apex -eq "no1kmedi.com") {
        $fixture = Join-Path $PSScriptRoot "data\hostinger_full_exit\no1kmedi_cloudflare_zone_v1.json"
        if (-not (Test-Path -LiteralPath $fixture)) { throw "Missing fixture: $fixture" }
        $j = Get-Content -LiteralPath $fixture -Raw -Encoding UTF8 | ConvertFrom-Json
        if ([string]::IsNullOrWhiteSpace($j.zone_id)) { throw "fixture.zone_id empty in $fixture" }
        $argsList += @("-ZoneId", [string]$j.zone_id)
    }
    if ($DryRun) { $argsList += "-DryRun" }

    & powershell -NoProfile -ExecutionPolicy Bypass -File $wrapper @argsList
    if ($LASTEXITCODE -gt $worst) { $worst = $LASTEXITCODE }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARN: exit $LASTEXITCODE for $($r.LocalPart)@$($r.Apex) (see reports/cloudflare_email_routing_setup_latest.json)" -ForegroundColor Yellow
    }
}

exit $worst
