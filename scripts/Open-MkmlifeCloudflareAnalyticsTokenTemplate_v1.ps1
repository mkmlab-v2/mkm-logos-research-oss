# Opens Cloudflare dashboard with mkmlife.com Zone Read + Analytics Read pre-filled.
# After create: paste token value only into reports/cloudflare_mkmlife_analytics_token_secret_LOCAL.json
#   then: powershell -File scripts\Invoke-ApplyMkmlifeCfAnalyticsTokenFromSecret_v1.ps1
$perms = @(
    @{ key = "zone"; type = "read" },
    @{ key = "analytics"; type = "read" }
)
$json = ($perms | ConvertTo-Json -Compress)
$enc = [uri]::EscapeDataString($json)
$name = [uri]::EscapeDataString("MKM-mkmlife-analytics-v1")
$zoneId = "259a847ea3643566383972ebd3ede918"
$accountId = "646e42cf881ab43043c32430e99d9af4"
$url = "https://dash.cloudflare.com/profile/api-tokens?permissionGroupKeys=$enc&accountId=$accountId&zoneId=$zoneId&name=$name"
Write-Host "Opening: $url"
$url
