#Requires -Version 5.1
<#
.SYNOPSIS
  PUT /zones/{zone_id}/activation_check — rerun NS activation for pending zones.

.PARAMETER ZoneName
  Apex domain (e.g. personadiary.com).

.PARAMETER OutJson
  Report path (default reports/cloudflare_zone_activation_check_latest.json).
#>
param(
    [string]$ZoneName = "",
    [string]$ZoneId = "",
    [string]$OutJson = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Get-CloudflareToken {
    foreach ($k in @("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN")) {
        foreach ($scope in @("User", "Machine", "Process")) {
            $v = [Environment]::GetEnvironmentVariable($k, $scope)
            if (-not [string]::IsNullOrWhiteSpace($v)) { return $v.Trim() }
        }
    }
    return $null
}

$tok = Get-CloudflareToken
if ([string]::IsNullOrWhiteSpace($tok)) { throw "Set CLOUDFLARE_API_TOKEN or CF_API_TOKEN." }

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = Join-Path $root "reports\cloudflare_zone_activation_check_latest.json"
}

$headers = @{
    Authorization = "Bearer $tok"
    Accept          = "application/json"
}
if ([string]::IsNullOrWhiteSpace($ZoneName) -and [string]::IsNullOrWhiteSpace($ZoneId)) {
    throw "Provide -ZoneName or -ZoneId"
}
if (-not [string]::IsNullOrWhiteSpace($ZoneId)) {
    $zoneId = $ZoneId.Trim()
    $getUri = "https://api.cloudflare.com/client/v4/zones/$zoneId"
    $zone = (Invoke-RestMethod -Uri $getUri -Headers $headers -Method Get).result
    if ($null -eq $zone) { throw "No zone for id $zoneId" }
    $ZoneName = [string]$zone.name
    $statusBefore = [string]$zone.status
}
else {
    $enc = [uri]::EscapeDataString($ZoneName.Trim())
    $listUri = "https://api.cloudflare.com/client/v4/zones?name=$enc"
    $list = Invoke-RestMethod -Uri $listUri -Headers $headers -Method Get
    if (-not $list.success -or @($list.result).Count -lt 1) {
        throw "No zone found for $ZoneName"
    }
    $zone = @($list.result)[0]
    $zoneId = [string]$zone.id
    $statusBefore = [string]$zone.status
}

$actUri = "https://api.cloudflare.com/client/v4/zones/$zoneId/activation_check"
$act = Invoke-RestMethod -Uri $actUri -Headers $headers -Method Put

Start-Sleep -Seconds 8
$zone2 = (Invoke-RestMethod -Uri "https://api.cloudflare.com/client/v4/zones/$zoneId" -Headers $headers -Method Get).result
$statusAfter = [string]$zone2.status

$payload = [ordered]@{
    schema           = "cloudflare_zone_activation_check_v1"
    generated_at_utc = [datetime]::UtcNow.ToString("o")
    zone_name        = $ZoneName
    zone_id          = $zoneId
    status_before    = $statusBefore
    status_after     = $statusAfter
    activation_put   = @{
        success = [bool]$act.success
        errors  = @($act.errors)
        messages = @($act.messages)
    }
    active           = ($statusAfter -eq "active")
}

$dir = Split-Path -Parent $OutJson
if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
($payload | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $OutJson -Encoding UTF8
Write-Host "Wrote $OutJson" -ForegroundColor Green
Write-Host ($payload | ConvertTo-Json -Compress -Depth 4)
if (-not $payload.active) { exit 2 }
exit 0
