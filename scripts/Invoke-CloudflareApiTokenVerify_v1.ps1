#Requires -Version 5.1
<#
.SYNOPSIS
  Cloudflare GET /user/tokens/verify + optional read-only DNS API probes (no mutations).

.PARAMETER ProbeZoneNames
  Zones to probe: GET /zones?name= then GET /zones/:id/dns_records?per_page=1

.PARAMETER SkipDnsProbe
  Only run token verify.

.NOTES
  Env: CLOUDFLARE_API_TOKEN or CF_API_TOKEN. Output: reports/cloudflare_api_token_verify_latest.json
#>
param(
    [string[]]$ProbeZoneNames = @("jema-ai.com", "no1kmedi.com", "jemaai.cloud"),
    [switch]$SkipDnsProbe,
    [string]$OutJson = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Get-CloudflareToken {
    foreach ($k in @("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN")) {
        foreach ($scope in @("Process", "User", "Machine")) {
            $v = [Environment]::GetEnvironmentVariable($k, $scope)
            if (-not [string]::IsNullOrWhiteSpace($v)) { return @{ Token = $v.Trim(); Var = $k } }
        }
    }
    return $null
}

$tok = Get-CloudflareToken
if (-not $tok) {
    throw "Set CLOUDFLARE_API_TOKEN or CF_API_TOKEN first."
}

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = Join-Path $root "reports\cloudflare_api_token_verify_latest.json"
}

$headers = @{
    Authorization = "Bearer $($tok.Token)"
    Accept          = "application/json"
}
$uri = "https://api.cloudflare.com/client/v4/user/tokens/verify"
$raw = Invoke-WebRequest -Uri $uri -Method GET -Headers $headers -UseBasicParsing
$j = $raw.Content | ConvertFrom-Json
if (-not $j.success) { throw "verify success=false: $($raw.Content)" }

$policies = @()
$res = $j.result
if ($null -ne $res) {
    $polProp = $res.PSObject.Properties["policies"]
    if ($null -ne $polProp -and $polProp.Value) {
        foreach ($p in $polProp.Value) {
            $policies += [ordered]@{
                id                  = $p.id
                effect              = $p.effect
                resources           = $p.resources
                permission_groups   = $p.permission_groups
            }
        }
    }
}

$out = [ordered]@{
    schema           = "cloudflare_api_token_verify_v1"
    generated_at_utc = [datetime]::UtcNow.ToString("o")
    token_env_var    = $tok.Var
    result_id        = $(if ($res) { $res.id } else { $null })
    status           = $(if ($res) { $res.status } else { $null })
    policies         = @($policies)
    note_tunnel_vs_dns = "Cloudflare Tunnel API tokens usually do NOT include Zone DNS Read/Edit. For scripts/Invoke-JemaaiCloudCloudflareDnsEnsure_v1.ps1 create a separate token with Zone DNS Read + Edit on target zones."
    dns_probes       = @()
}

if (-not $SkipDnsProbe) {
    $base = "https://api.cloudflare.com/client/v4"
    foreach ($zn in $ProbeZoneNames) {
        if ([string]::IsNullOrWhiteSpace($zn)) { continue }
        $zt = $zn.Trim()
        $row = [ordered]@{ zone = $zt; zone_list_http = $null; zone_found = $false; zone_id = $null; dns_list_http = $null; dns_list_ok = $false }
        try {
            $zurl = "$base/zones?name=$([uri]::EscapeDataString($zt))"
            $zw = Invoke-WebRequest -Uri $zurl -Method GET -Headers $headers -UseBasicParsing
            $row.zone_list_http = [int]$zw.StatusCode
            $zj = $zw.Content | ConvertFrom-Json
            if ($zj.success -and $zj.result -and $zj.result.Count -gt 0) {
                $row.zone_found = $true
                $zid = [string]$zj.result[0].id
                $row.zone_id = $zid
                $durl = "$base/zones/$zid/dns_records?per_page=1"
                try {
                    $dw = Invoke-WebRequest -Uri $durl -Method GET -Headers $headers -UseBasicParsing
                    $row.dns_list_http = [int]$dw.StatusCode
                    $dj = $dw.Content | ConvertFrom-Json
                    $row.dns_list_ok = [bool]$dj.success
                }
                catch {
                    $ex = $_.Exception
                    $row.dns_list_http = 0
                    $row.dns_list_ok = $false
                    $row.dns_list_error = $ex.Message
                }
            }
        }
        catch {
            $row.zone_list_http = 0
            $row.zone_list_error = $_.Exception.Message
        }
        $out.dns_probes += [pscustomobject]$row
    }
}

$dir = Split-Path -Parent $OutJson
if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
($out | ConvertTo-Json -Depth 12) | Set-Content -LiteralPath $OutJson -Encoding UTF8
Write-Host "Wrote $OutJson" -ForegroundColor Green
Write-Host ($out | ConvertTo-Json -Depth 6)

exit 0
