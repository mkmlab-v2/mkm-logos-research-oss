#Requires -Version 5.1
<#
.SYNOPSIS
  Cloudflare API: POST /client/v4/zones — add a zone to an account (one-time / infra).

.DESCRIPTION
  Requires API token permission: com.cloudflare.api.account.zone.create (Account · Zone · Create),
  not only Zone DNS Edit. Dashboard URL contains account id:
  https://dash.cloudflare.com/<ACCOUNT_ID>/home/overview

.PARAMETER AccountId
  Cloudflare account id (32-char hex), e.g. from dashboard URL.

.PARAMETER ZoneName
  Apex domain to add, e.g. jemaai.cloud

.PARAMETER JumpStart
  Ask Cloudflare to scan for existing DNS records (default true).

.PARAMETER WhatIf
  Only GET /zones?name= to see if zone already exists under this token (no POST).

.PARAMETER OutJson
  Report path (default reports/cloudflare_zone_create_latest.json).

.NOTES
  Env: CLOUDFLARE_API_TOKEN or CF_API_TOKEN. After zone creation, set registrar NS to result.name_servers,
  then run Run-CloudflareDnsEnsureChain_v1.ps1 (DNS-only token is enough for that step).
#>
param(
    [Parameter(Mandatory = $true)][string]$AccountId,
    [Parameter(Mandatory = $true)][string]$ZoneName,
    [bool]$JumpStart = $true,
    [switch]$WhatIf,
    [string]$OutJson = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Get-CloudflareToken {
    foreach ($k in @("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN")) {
        foreach ($scope in @("User", "Machine", "Process")) {
            $v = [Environment]::GetEnvironmentVariable($k, $scope)
            if (-not [string]::IsNullOrWhiteSpace($v)) { return @{ Token = $v.Trim(); Var = $k } }
        }
    }
    return $null
}

function Invoke-CfApi {
    param(
        [string]$Method,
        [string]$Uri,
        [hashtable]$Headers,
        [string]$Body = $null
    )
    try {
        if ($Method -match '^(GET|HEAD)$') {
            $raw = Invoke-WebRequest -Uri $Uri -Method $Method -Headers $Headers -UseBasicParsing
        }
        elseif ($null -ne $Body) {
            $raw = Invoke-WebRequest -Uri $Uri -Method $Method -Headers $Headers -UseBasicParsing `
                -ContentType "application/json; charset=utf-8" -Body $Body
        }
        else {
            $raw = Invoke-WebRequest -Uri $Uri -Method $Method -Headers $Headers -UseBasicParsing
        }
        return @{ Ok = $true; Status = [int]$raw.StatusCode; Text = $raw.Content }
    }
    catch {
        $text = $null
        $status = 0
        $ex = $_.Exception
        $resp = $null
        try {
            if ($null -ne $ex -and $ex.PSObject.Properties.Match("Response").Count -gt 0) { $resp = $ex.Response }
        }
        catch { $resp = $null }
        if ($null -ne $resp) {
            try {
                $status = [int]$resp.StatusCode
                $sr = New-Object System.IO.StreamReader($resp.GetResponseStream())
                $text = $sr.ReadToEnd()
                $sr.Close()
            }
            catch { $text = $ex.Message }
        }
        else {
            $text = if ($ex -and $ex.Message) { $ex.Message } else { "$ex" }
        }
        return @{ Ok = $false; Status = $status; Text = $text }
    }
}

$tok = Get-CloudflareToken
if (-not $tok) {
    throw "Set CLOUDFLARE_API_TOKEN or CF_API_TOKEN. See .env.example Cloudflare section."
}

$aid = $AccountId.Trim()
if ($aid.Length -lt 32) { throw "AccountId looks invalid (expected 32-char hex from dashboard URL)." }

$zn = $ZoneName.Trim().ToLowerInvariant()
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = Join-Path $root "reports\cloudflare_zone_create_latest.json"
}

$headers = @{
    Authorization = "Bearer $($tok.Token)"
    Accept          = "application/json"
}
$base = "https://api.cloudflare.com/client/v4"

$out = [ordered]@{
    schema           = "cloudflare_zone_create_v1"
    generated_at_utc = [datetime]::UtcNow.ToString("o")
    account_id       = $aid
    zone_name        = $zn
    token_env_var    = $tok.Var
    what_if          = [bool]$WhatIf
    action           = "pending"
    http_status      = $null
    zone_id          = $null
    zone_status      = $null
    name_servers     = @()
    errors           = @()
    note             = "Token needs Account Zone Create (not DNS-only). Permission id in dashboard: Zone · Create on this account."
}

$check = Invoke-CfApi -Method GET -Uri "$base/zones?name=$([uri]::EscapeDataString($zn))" -Headers $headers
if ($check.Ok) {
    $cj = $check.Text | ConvertFrom-Json
    if ($cj.success -and $cj.result -and @($cj.result).Count -gt 0) {
        $z0 = $cj.result[0]
        $out.action = "already_exists"
        $out.zone_id = $z0.id
        $out.zone_status = $z0.status
        $out.name_servers = @($z0.name_servers)
        $out.http_status = $check.Status
        $out.note = "Zone already in account; no POST needed. Point registrar NS to name_servers if not yet."
        $out | ConvertTo-Json -Depth 8 | Set-Content -Path $OutJson -Encoding UTF8
        Write-Host "Wrote $OutJson"
        Write-Host ($out | ConvertTo-Json -Compress -Depth 6)
        exit 0
    }
}

if ($WhatIf) {
    $out.action = "what_if_only"
    $out.http_status = $check.Status
    if ($check.Ok) {
        $out.errors = @()
        $out.note = "Zone not listed under this token yet (list OK); would POST /zones (not executed)."
    }
    else {
        $out.errors = @($check.Text)
        $out.note = "GET /zones failed; fix token then retry. Would POST /zones (not executed)."
    }
    $out | ConvertTo-Json -Depth 8 | Set-Content -Path $OutJson -Encoding UTF8
    Write-Host "Wrote $OutJson"
    exit 0
}

$bodyObj = @{
    name    = $zn
    account = @{ id = $aid }
}
if ($JumpStart) { $bodyObj["jump_start"] = $true }
$body = $bodyObj | ConvertTo-Json -Depth 5

$post = Invoke-CfApi -Method POST -Uri "$base/zones" -Headers $headers -Body $body
$out.http_status = $post.Status

try {
    $pj = $post.Text | ConvertFrom-Json
}
catch {
    $out.action = "parse_error"
    $out.errors = @($post.Text)
    $out | ConvertTo-Json -Depth 8 | Set-Content -Path $OutJson -Encoding UTF8
    throw "Non-JSON response: $($post.Text)"
}

if (-not $pj.success) {
    $out.action = "failed"
    foreach ($e in @($pj.errors)) {
        $out.errors += [ordered]@{ code = $e.code; message = $e.message }
    }
    $out | ConvertTo-Json -Depth 8 | Set-Content -Path $OutJson -Encoding UTF8
    Write-Host "Wrote $OutJson"
    Write-Host ($out | ConvertTo-Json -Compress -Depth 6)
    if ($post.Status -eq 403) {
        Write-Host "FIX: Create a new API token with permission 'Account' · 'Zone' · 'Create' (or All zones from an account including Create), then sync to User env and re-run this script."
    }
    exit 1
}

$res = $pj.result
$out.action = "created"
$out.zone_id = $res.id
$out.zone_status = $res.status
$out.name_servers = @($res.name_servers)

$out | ConvertTo-Json -Depth 8 | Set-Content -Path $OutJson -Encoding UTF8
Write-Host "Wrote $OutJson"
Write-Host ($out | ConvertTo-Json -Compress -Depth 6)
exit 0
