# Opens Cloudflare dashboard with mkmlife deploy token pre-filled (account Workers + zone Routes).
# Zone-scoped Workers Routes Edit is REQUIRED for wrangler custom_domain routes sync.
# After create/edit: paste token into reports/cloudflare_mkmlife_deploy_token_secret_LOCAL.json
#   then: powershell -File scripts\Invoke-MkmlifeCfDeployTokenReadiness_v1.ps1 -ApplyIfPresent
# Repair one-click: scripts\Invoke-RepairMkmlifeCfDeployToken_v1.ps1
$accountPerms = @(
    @{ key = "workers_scripts"; type = "edit" },
    @{ key = "workers_kv_storage"; type = "edit" },
    @{ key = "account"; type = "read" }
)
$zonePerms = @(
    @{ key = "workers_routes"; type = "edit" },
    @{ key = "zone"; type = "read" }
)
$userPerms = @(
    @{ key = "user"; type = "read" }
)
$all = $accountPerms + $zonePerms + $userPerms
$json = ($all | ConvertTo-Json -Compress)
$enc = [uri]::EscapeDataString($json)
$name = [uri]::EscapeDataString("MKM-mkmlife-deploy-v2-routes")
$accountId = "646e42cf881ab43043c32430e99d9af4"
$zoneId = "259a847ea3643566383972ebd3ede918"
$url = "https://dash.cloudflare.com/profile/api-tokens?permissionGroupKeys=$enc&accountId=$accountId&zoneId=$zoneId&name=$name"
Write-Host "Opening mkmlife deploy token template (zone=$zoneId):"
Write-Host $url
Start-Process $url
Write-Host ""
Write-Host "Required permissions:" -ForegroundColor Cyan
Write-Host "  Account: Workers Scripts Edit, Workers KV Storage Edit" -ForegroundColor DarkGray
Write-Host "  Zone mkmlife.com: Workers Routes Edit, Zone Read" -ForegroundColor DarkGray
Write-Host "  User: User Details Read (optional — removes wrangler email warning)" -ForegroundColor DarkGray
