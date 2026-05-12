#Requires -Version 5.1
<#
.SYNOPSIS
  Cloudflare API: ensure www -> apex CNAME (proxied) for a zone (default jemaai.cloud).

.DESCRIPTION
  Uses Cloudflare v4 REST. Token must NOT be committed; read from User/Process env only.

  Env (first non-empty wins for token): CLOUDFLARE_API_TOKEN, CF_API_TOKEN
  Optional: CLOUDFLARE_ZONE_ID — used only when GET /zones/:id confirms the zone name matches -ZoneName (avoids cross-zone 403).

.PARAMETER ZoneName
  Cloudflare zone apex, e.g. jemaai.cloud or jema-ai.com

.PARAMETER WwwLabel
  Relative host label for www (default www -> www.<ZoneName>)

.PARAMETER CnameTarget
  CNAME content (FQDN). Default: same as ZoneName (apex of that zone).

.PARAMETER Proxied
  Orange-cloud (default true).

.PARAMETER WhatIf
  Resolve zone and print planned action only (no POST/PATCH).

.PARAMETER AllowDeleteConflictingWwwHost
  If POST returns 81053 because www has A/AAAA only, delete those records at this exact host and retry POST once (destructive; use with chain automation only when apex CNAME is intended).

.PARAMETER OutJson
  Report path (default reports/jemaai_cloud_cloudflare_dns_ensure_latest.json).

.NOTES
  Required token scope: Zone.DNS:Edit (and Zone:Read for zone list / zone detail).
#>
param(
    [string]$ZoneName = "jemaai.cloud",
    [string]$WwwLabel = "www",
    [string]$CnameTarget = "",
    [bool]$Proxied = $true,
    [switch]$WhatIf,
    [switch]$AllowDeleteConflictingWwwHost,
    [string]$OutJson = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Get-CloudflareToken {
    foreach ($k in @("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN")) {
        $v = [Environment]::GetEnvironmentVariable($k, "Process")
        if ([string]::IsNullOrWhiteSpace($v)) { $v = [Environment]::GetEnvironmentVariable($k, "User") }
        if ([string]::IsNullOrWhiteSpace($v)) { $v = [Environment]::GetEnvironmentVariable($k, "Machine") }
        if (-not [string]::IsNullOrWhiteSpace($v)) { return @{ Token = $v.Trim(); Var = $k } }
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
        $er = $_
        $text = $null
        if ($er.ErrorDetails -and $er.ErrorDetails.Message) {
            $text = $er.ErrorDetails.Message.Trim()
        }
        $status = 0
        $ex = $er.Exception
        $resp = $null
        try {
            if ($null -ne $ex -and $ex.PSObject.Properties.Match("Response").Count -gt 0) {
                $resp = $ex.Response
            }
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
    throw "Set CLOUDFLARE_API_TOKEN or CF_API_TOKEN (User env or Process). Never commit the token. See .env.example Cloudflare section."
}

$target = $CnameTarget.Trim()
if ([string]::IsNullOrWhiteSpace($target)) { $target = $ZoneName.Trim() }

$fqdnWww = if ($WwwLabel -eq "@" -or [string]::IsNullOrWhiteSpace($WwwLabel)) { $ZoneName } else { "$WwwLabel.$ZoneName" }

$headers = @{
    Authorization = "Bearer $($tok.Token)"
    Accept          = "application/json"
}

$base = "https://api.cloudflare.com/client/v4"
$zoneId = ""

# Optional env zone id: only use if it matches this run's ZoneName (avoids wrong zone -> DNS 403).
$envZid = [Environment]::GetEnvironmentVariable("CLOUDFLARE_ZONE_ID", "Process")
if ([string]::IsNullOrWhiteSpace($envZid)) { $envZid = [Environment]::GetEnvironmentVariable("CLOUDFLARE_ZONE_ID", "User") }
if ([string]::IsNullOrWhiteSpace($envZid)) { $envZid = [Environment]::GetEnvironmentVariable("CLOUDFLARE_ZONE_ID", "Machine") }
if (-not [string]::IsNullOrWhiteSpace($envZid)) {
    $zr0 = Invoke-CfApi -Method GET -Uri "$base/zones/$($envZid.Trim())" -Headers $headers
    if ($zr0.Ok) {
        $z0 = $zr0.Text | ConvertFrom-Json
        if ($z0.success -and $z0.result -and ([string]$z0.result.name).Equals($ZoneName, [System.StringComparison]::OrdinalIgnoreCase)) {
            $zoneId = $envZid.Trim()
        }
    }
}

if ([string]::IsNullOrWhiteSpace($zoneId)) {
    $zr = Invoke-CfApi -Method GET -Uri "$base/zones?name=$([uri]::EscapeDataString($ZoneName))" -Headers $headers
    if (-not $zr.Ok) { throw "Zone list failed HTTP $($zr.Status): $($zr.Text)" }
    $zj = $zr.Text | ConvertFrom-Json
    if (-not $zj.success) { throw "Cloudflare zones API success=false: $($zr.Text)" }
    if (-not $zj.result -or $zj.result.Count -lt 1) {
        throw "No Cloudflare zone named '$ZoneName'. Add the zone in Cloudflare first, then point registrar NS to Cloudflare."
    }
    $zoneId = [string]$zj.result[0].id
}

$listUri = "$base/zones/$zoneId/dns_records?type=CNAME&name=$([uri]::EscapeDataString($fqdnWww))"
$lr = Invoke-CfApi -Method GET -Uri $listUri -Headers $headers
$lj = $null
if ($lr.Ok) {
    $lj = $lr.Text | ConvertFrom-Json
}
if (-not $lr.Ok -or ($null -eq $lj) -or (-not $lj.success)) {
    $fallback = "$base/zones/$zoneId/dns_records?type=CNAME&per_page=100"
    $lr2 = Invoke-CfApi -Method GET -Uri $fallback -Headers $headers
    if (-not $lr2.Ok) {
        $hint = "Token needs Zone.DNS:Read and Zone.DNS:Edit for zone '$ZoneName'. Raw: HTTP $($lr.Status) then $($lr2.Status)."
        throw "DNS list failed. $hint`nFirst: $($lr.Text)`nSecond: $($lr2.Text)"
    }
    $lj2 = $lr2.Text | ConvertFrom-Json
    if (-not $lj2.success) { throw "Cloudflare dns_records list success=false: $($lr2.Text)" }
    $match = @($lj2.result | Where-Object { $_.name -eq $fqdnWww })
    if ($match.Count -gt 0) {
        $lj = [pscustomobject]@{ success = $true; result = @($match[0]) }
    }
    else {
        $lj = [pscustomobject]@{ success = $true; result = @() }
    }
}
if (-not $lj.success) { throw "Cloudflare dns_records list success=false: $($lr.Text)" }

$existing = $null
if ($lj.result -and $lj.result.Count -gt 0) {
    $existing = $lj.result[0]
}

$plan = [ordered]@{
    schema           = "jemaai_cloud_cloudflare_dns_ensure_v1"
    generated_at_utc = [datetime]::UtcNow.ToString("o")
    zone_name        = $ZoneName
    zone_id          = $zoneId
    fqdn_www         = $fqdnWww
    cname_target      = $target
    proxied           = $Proxied
    token_source      = $tok.Var
    what_if           = [bool]$WhatIf
    action            = "noop"
    record_id         = $null
}

if ($null -eq $existing) {
    $plan.action = "create"
    if ($WhatIf) {
        $plan.note = "Would POST CNAME $fqdnWww -> $target proxied=$Proxied"
    }
    else {
        $bodyObj = @{
            type    = "CNAME"
            name    = $WwwLabel
            content = $target
            ttl     = 1
            proxied = $Proxied
        }
        $body = ($bodyObj | ConvertTo-Json -Compress)
        $pr = Invoke-CfApi -Method POST -Uri "$base/zones/$zoneId/dns_records" -Headers $headers -Body $body
        $patchedAfter81053 = $false
        if (-not $pr.Ok) {
            if ($pr.Text -match '"code":81053') {
                $nr = Invoke-CfApi -Method GET -Uri "$base/zones/$zoneId/dns_records?name=$([uri]::EscapeDataString($fqdnWww))" -Headers $headers
                if ($nr.Ok) {
                    $nj = $nr.Text | ConvertFrom-Json
                    $crec = $null
                    if ($nj.success -and $nj.result) {
                        $matches = @($nj.result | Where-Object { $_.type -eq "CNAME" -and $_.name -eq $fqdnWww })
                        if ($matches.Count -gt 0) { $crec = $matches[0] }
                    }
                    if ($null -ne $crec) {
                        $bodyP = ($bodyObj | ConvertTo-Json -Compress)
                        $prPatch = Invoke-CfApi -Method PATCH -Uri "$base/zones/$zoneId/dns_records/$($crec.id)" -Headers $headers -Body $bodyP
                        if ($prPatch.Ok) {
                            $pjPatch = $prPatch.Text | ConvertFrom-Json
                            if ($pjPatch.success) {
                                $plan.action = "patched"
                                $plan.record_id = $crec.id
                                $plan.note = "POST returned 81053; PATCH existing CNAME at $fqdnWww"
                                $patchedAfter81053 = $true
                            }
                        }
                    }
                    else {
                        $anyHost = @()
                        if ($nj.success -and $nj.result) {
                            $anyHost = @($nj.result | Where-Object { $_.name -eq $fqdnWww })
                        }
                        if ($anyHost.Count -gt 0) {
                            $types = ($anyHost | ForEach-Object { $_.type }) -join ","
                            if ($AllowDeleteConflictingWwwHost) {
                                foreach ($rec in $anyHost) {
                                    if ($rec.type -eq "A" -or $rec.type -eq "AAAA") {
                                        $del = Invoke-CfApi -Method DELETE -Uri "$base/zones/$zoneId/dns_records/$($rec.id)" -Headers $headers
                                        if (-not $del.Ok) {
                                            throw "DNS delete $($rec.type) id=$($rec.id) failed HTTP $($del.Status): $($del.Text)"
                                        }
                                    }
                                }
                                $plan.note = "81053: deleted A/AAAA at $fqdnWww ; retrying POST"
                                $prRetry = Invoke-CfApi -Method POST -Uri "$base/zones/$zoneId/dns_records" -Headers $headers -Body $body
                                if (-not $prRetry.Ok) { throw "DNS POST after delete failed HTTP $($prRetry.Status): $($prRetry.Text)" }
                                $pjR = $prRetry.Text | ConvertFrom-Json
                                if (-not $pjR.success) { throw "DNS POST after delete success=false: $($prRetry.Text)" }
                                $plan.action = "created"
                                $plan.record_id = $pjR.result.id
                                $patchedAfter81053 = $true
                            }
                            else {
                                throw "DNS 81053: host $fqdnWww exists (types: $types). Pass -AllowDeleteConflictingWwwHost to delete A/AAAA at this host only, or fix in Cloudflare UI."
                            }
                        }
                    }
                }
            }
            if (-not $patchedAfter81053) {
                if ($pr.Text -match '"code":81057' -or $pr.Text -match "already exists") {
                    $plan.note = "Create rejected duplicate; re-run to PATCH after list refresh."
                }
                throw "DNS create failed HTTP $($pr.Status): $($pr.Text)"
            }
        }
        if (-not $patchedAfter81053 -and $pr.Ok) {
            $pj = $pr.Text | ConvertFrom-Json
            if (-not $pj.success) { throw "DNS create success=false: $($pr.Text)" }
            $plan.action = "created"
            $plan.record_id = $pj.result.id
        }
    }
}
else {
    $plan.record_id = $existing.id
    $needPatch = ($existing.content -ne $target) -or ([bool]$existing.proxied -ne $Proxied)
    if (-not $needPatch) {
        $plan.action = "noop"
        $plan.note = "CNAME already matches content=$($existing.content) proxied=$($existing.proxied)"
    }
    else {
        $plan.action = "patch"
        if ($WhatIf) {
            $plan.note = "Would PATCH record $($existing.id) to content=$target proxied=$Proxied"
        }
        else {
            $bodyObj = @{
                type    = "CNAME"
                name    = $WwwLabel
                content = $target
                ttl     = 1
                proxied = $Proxied
            }
            $body = ($bodyObj | ConvertTo-Json -Compress)
            $pr = Invoke-CfApi -Method PATCH -Uri "$base/zones/$zoneId/dns_records/$($existing.id)" -Headers $headers -Body $body
            if (-not $pr.Ok) { throw "DNS patch failed HTTP $($pr.Status): $($pr.Text)" }
            $pj = $pr.Text | ConvertFrom-Json
            if (-not $pj.success) { throw "DNS patch success=false: $($pr.Text)" }
            $plan.action = "patched"
        }
    }
}

if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    $OutJson = Join-Path $root "reports\jemaai_cloud_cloudflare_dns_ensure_latest.json"
}
$dir = Split-Path -Parent $OutJson
if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
($plan | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $OutJson -Encoding UTF8
Write-Host "Wrote $OutJson" -ForegroundColor Green
Write-Host ($plan | ConvertTo-Json -Compress)

exit 0
