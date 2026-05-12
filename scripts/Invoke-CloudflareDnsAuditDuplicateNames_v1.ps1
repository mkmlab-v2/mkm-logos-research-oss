#Requires -Version 5.1
<#
.SYNOPSIS
  Cloudflare read-only audit: same hostname + same record type appearing more than once (e.g. two A on assets); plus names that use multiple types (apex A+MX+TXT).

.PARAMETER ZoneNames
  Comma-separated apex zones (default: jemaai.cloud).

.PARAMETER PerPage
  Page size for GET /dns_records (max 500; default 100).

.PARAMETER OutJson
  Report path (default reports/cloudflare_dns_audit_duplicates_latest.json).

.NOTES
  Env: CLOUDFLARE_API_TOKEN or CF_API_TOKEN (User preferred). Zone DNS Read required.
#>
param(
    [string]$ZoneNames = "jemaai.cloud",
    [int]$PerPage = 100,
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

function Invoke-CfGet {
    param([string]$Uri, [hashtable]$Headers)
    try {
        $raw = Invoke-WebRequest -Uri $Uri -Method GET -Headers $Headers -UseBasicParsing
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
        else { $text = if ($ex -and $ex.Message) { $ex.Message } else { "$ex" } }
        return @{ Ok = $false; Status = $status; Text = $text }
    }
}

$tok = Get-CloudflareToken
if (-not $tok) { throw "Set CLOUDFLARE_API_TOKEN or CF_API_TOKEN." }

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = Join-Path $root "reports\cloudflare_dns_audit_duplicates_latest.json"
}

$pp = [Math]::Min(500, [Math]::Max(1, $PerPage))
$headers = @{
    Authorization = "Bearer $($tok.Token)"
    Accept          = "application/json"
}
$base = "https://api.cloudflare.com/client/v4"

$flatZones = [System.Collections.Generic.List[string]]::new()
foreach ($part in ($ZoneNames -split ',')) {
    $t = $part.Trim()
    if ($t) { $flatZones.Add($t) | Out-Null }
}
if ($flatZones.Count -eq 0) { throw "No zones in -ZoneNames." }

$zonesOut = [System.Collections.Generic.List[object]]::new()

foreach ($zn in $flatZones) {
    $zr = Invoke-CfGet -Uri "$base/zones?name=$([uri]::EscapeDataString($zn))" -Headers $headers
    if (-not $zr.Ok) { throw "Zone list failed HTTP $($zr.Status): $($zr.Text)" }
    $zj = $zr.Text | ConvertFrom-Json
    if (-not $zj.success) { throw "zones success=false: $($zr.Text)" }
    if (@($zj.result).Count -lt 1) { throw "No zone named '$zn'." }
    $zoneId = [string](@($zj.result)[0].id)

    $allRecs = [System.Collections.Generic.List[object]]::new()
    $page = 1
    while ($true) {
        $uri = "$base/zones/$zoneId/dns_records?page=$page&per_page=$pp"
        $dr = Invoke-CfGet -Uri $uri -Headers $headers
        if (-not $dr.Ok) { throw "dns_records list failed HTTP $($dr.Status): $($dr.Text)" }
        $dj = $dr.Text | ConvertFrom-Json
        if (-not $dj.success) { throw "dns_records success=false: $($dr.Text)" }
        foreach ($rec in @($dj.result)) {
            $nm = [string]$rec.name
            $tp = [string]$rec.type
            $allRecs.Add([pscustomobject]@{
                    id        = $rec.id
                    name      = $nm
                    type      = $tp
                    name_type = "$nm|$tp"
                    content   = [string]$rec.content
                    proxied   = [bool]$rec.proxied
                    ttl       = $rec.ttl
                }) | Out-Null
        }
        $ri = $dj.result_info
        $totalPages = 1
        if ($null -ne $ri -and $null -ne $ri.total_pages) { $totalPages = [int]$ri.total_pages }
        if ($page -ge $totalPages) { break }
        $page++
    }

    $byNameType = $allRecs | Group-Object name_type
    $dupes = [System.Collections.Generic.List[object]]::new()
    foreach ($g in $byNameType) {
        if ($g.Count -le 1) { continue }
        $rows = @($g.Group)
        $parts = $g.Name -split '\|', 2
        $dupes.Add([ordered]@{
                name    = $parts[0]
                type    = $parts[1]
                count   = $g.Count
                records = @($rows)
            }) | Out-Null
    }

    $byNameOnly = $allRecs | Group-Object name
    $multiTypeAtName = [System.Collections.Generic.List[object]]::new()
    foreach ($g in $byNameOnly) {
        $types = @($g.Group | Select-Object -ExpandProperty type -Unique)
        if ($types.Count -le 1) { continue }
        $multiTypeAtName.Add([ordered]@{
                name  = $g.Name
                types = @($types)
                count = $g.Count
            }) | Out-Null
    }

    $zonesOut.Add([ordered]@{
            zone_name                = $zn
            zone_id                  = $zoneId
            total_records            = $allRecs.Count
            duplicate_name_type      = @($dupes)
            duplicate_name_type_n    = $dupes.Count
            names_with_multiple_types = @($multiTypeAtName)
        }) | Out-Null
}

$payload = [ordered]@{
    schema           = "cloudflare_dns_audit_duplicates_v1"
    generated_at_utc = [datetime]::UtcNow.ToString("o")
    token_env_var    = $tok.Var
    note             = "Multiple MX (or NS) on the same hostname are often intentional. Review duplicate A/AAAA/CNAME first."
    zones            = @($zonesOut)
}

$dir = Split-Path -Parent $OutJson
if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
($payload | ConvertTo-Json -Depth 12) | Set-Content -LiteralPath $OutJson -Encoding UTF8
Write-Host "Wrote $OutJson" -ForegroundColor Green
Write-Host ($payload | ConvertTo-Json -Compress -Depth 5)

exit 0
