<#
.SYNOPSIS
  LinkedIn publish prep: rebuild paste files, clipboard primary, open feed, emit OpenChrome agent handoff.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-MarketingLinkedInPublishPrep_v1.ps1
  powershell ... -ItemId compression_governance_moat_w12
#>
param(
    [string]$WorkspaceRoot = "",
    [string]$ItemId = "",
    [string]$PrimaryId = "",
    [switch]$SkipRebuild,
    [switch]$NoClipboard,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$root = if ($WorkspaceRoot) { (Resolve-Path -LiteralPath $WorkspaceRoot).Path } else { Split-Path -Parent $PSScriptRoot }
$prep = Join-Path $root "scripts\publish_marketing_linkedin_feed_prep_v1.py"

$argsList = @($prep, "--emit-agent-request")
if ($SkipRebuild) { $argsList += "--skip-rebuild" }
if ($NoClipboard) { $argsList += "--no-clipboard" }
if ($NoBrowser) { $argsList += "--no-browser" }
if ($ItemId) { $argsList += @("--item-id", $ItemId) }
if ($PrimaryId) { $argsList += @("--primary-id", $PrimaryId) }

& py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[DONE] Prep: reports/marketing/marketing_linkedin_feed_prep_latest.json" -ForegroundColor Green
Write-Host "[DONE] Agent handoff: reports/marketing/linkedin_openchrome_publish_request_latest.json" -ForegroundColor Green
Write-Host '[HINT] OpenChrome headed publish; closure: py scripts/marketing_linkedin_publish_closure_v1.py --phrase published' -ForegroundColor Cyan
exit 0
