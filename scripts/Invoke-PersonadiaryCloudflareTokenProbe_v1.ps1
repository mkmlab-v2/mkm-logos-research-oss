#Requires -Version 5.1
<#
.SYNOPSIS
  Probe Cloudflare token access for personadiary.com zone (no secrets in output).
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$fixture = Join-Path $root "scripts\data\hostinger_full_exit\personadiary_cloudflare_zone_v1.json"
$fx = Get-Content -LiteralPath $fixture -Raw | ConvertFrom-Json
$zoneId = [string]$fx.zone_id
$zoneName = [string]$fx.apex

function Get-Tok {
    foreach ($k in @("MKM_CLOUDFLARE_PERSONADIARY_DNS_TOKEN", "CLOUDFLARE_API_TOKEN", "CF_API_TOKEN")) {
        foreach ($scope in @("User", "Process", "Machine")) {
            $v = [Environment]::GetEnvironmentVariable($k, $scope)
            if (-not [string]::IsNullOrWhiteSpace($v)) { return @{ Var = $k; Scope = $scope } }
        }
    }
    $envPath = Join-Path $root ".env"
    if (Test-Path -LiteralPath $envPath) {
        foreach ($line in Get-Content -LiteralPath $envPath) {
            if ($line -match '^(?:MKM_CLOUDFLARE_PERSONADIARY_DNS_TOKEN|CLOUDFLARE_API_TOKEN|CF_API_TOKEN)=(.+)$') {
                return @{ Var = "dotenv"; Scope = "file" }
            }
        }
    }
    return $null
}

function Get-TokValue {
    param($meta)
    if ($meta.Var -eq "dotenv") {
        foreach ($line in Get-Content -LiteralPath (Join-Path $root ".env")) {
            if ($line -match '^(MKM_CLOUDFLARE_PERSONADIARY_DNS_TOKEN|CLOUDFLARE_API_TOKEN|CF_API_TOKEN)=(.+)$') {
                return $matches[1].Trim()
            }
        }
    }
    return [Environment]::GetEnvironmentVariable($meta.Var, $meta.Scope)
}

function Invoke-Cf {
    param([string]$Uri, [hashtable]$Headers)
    try {
        $r = Invoke-WebRequest -Uri $Uri -Headers $Headers -UseBasicParsing
        return @{ ok = $true; status = [int]$r.StatusCode; body = $r.Content }
    }
    catch {
        $st = 0
        $body = $null
        if ($_.Exception.Response) {
            $st = [int]$_.Exception.Response.StatusCode
            $sr = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $body = $sr.ReadToEnd()
            $sr.Close()
        }
        return @{ ok = $false; status = $st; body = $body }
    }
}

$meta = Get-Tok
if (-not $meta) {
    Write-Host '{"ok":false,"error":"no_token"}'
    exit 2
}
$token = Get-TokValue -meta $meta
$h = @{ Authorization = "Bearer $token"; Accept = "application/json" }
$base = "https://api.cloudflare.com/client/v4"

$checks = [ordered]@{
    token_source = "$($meta.Var)@$($meta.Scope)"
    zone_name    = $zoneName
    zone_id      = $zoneId
    zone_by_id   = $null
    zone_list    = $null
    dns_list     = $null
    fix          = @()
}

$r1 = Invoke-Cf -Uri "$base/zones/$zoneId" -Headers $h
$checks.zone_by_id = @{ http = $r1.status; ok = $r1.ok }
if ($r1.ok) {
    $j = $r1.body | ConvertFrom-Json
    $checks.zone_by_id.name = $j.result.name
    $checks.zone_by_id.success = $j.success
}

$r2 = Invoke-Cf -Uri "$base/zones?name=$([uri]::EscapeDataString($zoneName))" -Headers $h
$checks.zone_list = @{ http = $r2.status; ok = $r2.ok }
if ($r2.ok) {
    $j2 = $r2.body | ConvertFrom-Json
    $checks.zone_list.count = @($j2.result).Count
    $checks.zone_list.success = $j2.success
}

$r3 = Invoke-Cf -Uri "$base/zones/$zoneId/dns_records?per_page=5" -Headers $h
$checks.dns_list = @{ http = $r3.status; ok = $r3.ok }
if ($r3.ok) {
    $j3 = $r3.body | ConvertFrom-Json
    $checks.dns_list.success = $j3.success
    $checks.dns_list.count = @($j3.result).Count
}

if (-not $checks.dns_list.ok) {
    $checks.fix += "API automation only: Zone.DNS Read+Edit if re-running DNS ensure script. Site may already be live (curl https://personadiary.com) — token not required for preview routing."
}
if (-not $checks.zone_by_id.ok) {
    $checks.fix += "토큰에 personadiary.com 존 Zone Read 포함 여부 확인"
}

$checks.ok = ($checks.zone_by_id.ok -and $checks.dns_list.ok)
$out = Join-Path $root "reports\personadiary_cloudflare_token_probe_latest.json"
$checks | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $out -Encoding UTF8
Write-Host ($checks | ConvertTo-Json -Compress)
exit $(if ($checks.ok) { 0 } else { 1 })
