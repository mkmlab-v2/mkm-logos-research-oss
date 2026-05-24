# Opens Cloudflare dashboard with mkmlab token permissions pre-filled (dns+zone_settings edit, zone read).
# After creating the token: paste into .env CLOUDFLARE_API_TOKEN, then:
#   powershell -NoProfile -ExecutionPolicy Bypass -File projects/bitcoin-trading/ops/windows-rehearsal/sync_required_env_to_user.ps1
#   py scripts/finalize_mkmlab_cloudflare_zone_v1.py --polls 2 --sleep-s 5
$perms = @(
    @{ key = "dns"; type = "edit" },
    @{ key = "zone_settings"; type = "edit" },
    @{ key = "zone"; type = "read" }
)
$json = ($perms | ConvertTo-Json -Compress)
$enc = [uri]::EscapeDataString($json)
$name = [uri]::EscapeDataString("MKM-mkmlab-zone-settings-dns-v1")
$url = "https://dash.cloudflare.com/profile/api-tokens?permissionGroupKeys=$enc&accountId=*&zoneId=all&name=$name"
Write-Host "Opening: $url"
Start-Process $url
