#Requires -Version 5.1
<#
.SYNOPSIS
  Open Cloudflare dashboard deep-links for mutda.ai OPEN_BETA route/DNS attach (Tier 3 Human).

.NOTES
  CF dash paths use zone NAME (mutda.ai), NOT zone_id.
  Wrong: /{account}/{zone_id}/dns/records  → Page not found
  Right: /{account}/mutda.ai/dns/records
#>
param(
    [string]$AccountId = "646e42cf881ab43043c32430e99d9af4",
    [string]$ZoneName = "mutda.ai",
    [string]$WorkerName = "mutda-news-open-beta"
)

$urls = @(
    # Domain DNS (correct: zone name, not zone id)
    "https://dash.cloudflare.com/$AccountId/$ZoneName/dns/records",
    # Workers routes on the zone
    "https://dash.cloudflare.com/$AccountId/$ZoneName/workers/routes",
    # Worker service overview
    "https://dash.cloudflare.com/$AccountId/workers/services/view/$WorkerName/production",
    # Worker settings / domains (custom domain attach)
    "https://dash.cloudflare.com/$AccountId/workers/services/view/$WorkerName/production/settings",
    # Domain overview
    "https://dash.cloudflare.com/$AccountId/$ZoneName"
)

Write-Host "Tier3 Human — mutda.ai OPEN_BETA route/DNS (zone NAME paths)" -ForegroundColor Cyan
Write-Host "1) DNS: apex 없으면 AAAA 100:: + Proxied(주황구름)"
Write-Host "2) Worker settings → Domains / Custom domains → Add mutda.ai"
Write-Host "   또는 Workers routes → Add: mutda.ai  and  mutda.ai/* → script mutda-news-open-beta"
Write-Host "3) After: py scripts/ensure_mutda_ai_open_beta_route_dns_v1.py --smoke-only"
Write-Host ""
foreach ($u in $urls) {
    Write-Host $u
    Start-Process $u
}
