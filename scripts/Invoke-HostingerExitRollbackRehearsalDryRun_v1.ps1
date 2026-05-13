#Requires -Version 5.1
<#
.SYNOPSIS
  Rollback rehearsal (dry-run): compare rollback_dns_template_v1.json to public DNS (read-only).

.DESCRIPTION
  For each domain entry with non-empty apex_a or www_cname_target, resolves current A/CNAME from the public resolver
  and reports match/mismatch. If www has no public CNAME but has A records (e.g. Cloudflare proxied flattening),
  compares www A to the A set of each template CNAME target. Does not call Cloudflare write APIs.

.PARAMETER TemplateJson
  Path to rollback_dns_template_v1.json.

.PARAMETER OutJson
  Output report (default reports/hostinger_exit_rollback_rehearsal_latest.json).
#>
param(
    [string]$TemplateJson = "",
    [string]$OutJson = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($TemplateJson)) {
    $TemplateJson = Join-Path $PSScriptRoot "data\hostinger_full_exit\rollback_dns_template_v1.json"
}
if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = Join-Path $root "reports\hostinger_exit_rollback_rehearsal_latest.json"
}

if (-not (Test-Path -LiteralPath $TemplateJson)) { throw "Missing: $TemplateJson" }
$tj = Get-Content -LiteralPath $TemplateJson -Raw -Encoding UTF8 | ConvertFrom-Json

$results = [System.Collections.Generic.List[object]]::new()

foreach ($prop in $tj.domains.PSObject.Properties) {
    $apex = $prop.Name
    $cfg = $prop.Value
    if ($null -eq $cfg) { continue }
    $wantApex = [string]$cfg.apex_a
    $wantWww = [string]$cfg.www_cname_target
    $wantApexList = @()
    $alProp = $cfg.PSObject.Properties['apex_a_list']
    if ($null -ne $alProp -and $null -ne $alProp.Value) {
        $rawA = $alProp.Value
        if ($rawA -is [System.Array]) {
            $wantApexList = @($rawA | ForEach-Object { [string]$_ } | Where-Object { $_ } | Select-Object -Unique)
        }
        elseif ($rawA -is [string] -and -not [string]::IsNullOrWhiteSpace($rawA)) {
            $wantApexList = @($rawA.Trim())
        }
    }
    if ($wantApexList.Count -eq 0 -and -not [string]::IsNullOrWhiteSpace($wantApex)) {
        $wantApexList = @($wantApex -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ } | Select-Object -Unique)
    }
    $wantWwwList = @()
    $wlProp = $cfg.PSObject.Properties['www_cname_list']
    if ($null -ne $wlProp -and $null -ne $wlProp.Value) {
        $rawW = $wlProp.Value
        if ($rawW -is [System.Array]) {
            $wantWwwList = @($rawW | ForEach-Object { [string]$_.Trim().TrimEnd('.') } | Where-Object { $_ } | Select-Object -Unique)
        }
        elseif ($rawW -is [string] -and -not [string]::IsNullOrWhiteSpace($rawW)) {
            $wantWwwList = @($rawW.Trim().TrimEnd('.'))
        }
    }
    if ($wantWwwList.Count -eq 0 -and -not [string]::IsNullOrWhiteSpace($wantWww)) {
        $wantWwwList = @($wantWww -split ',' | ForEach-Object { $_.Trim().TrimEnd('.') } | Where-Object { $_ } | Select-Object -Unique)
    }
    $row = [ordered]@{
        apex                   = $apex
        apex_a_template        = $wantApex
        apex_a_template_list   = @($wantApexList)
        apex_a_public          = @()
        apex_match             = $null
        www                    = "www.$apex"
        www_cname_template     = $wantWww
        www_cname_template_list = @($wantWwwList)
        www_cname_public       = @()
        www_a_public           = @()
        www_match              = $null
        www_match_mode         = $null
        skipped                = $false
    }

    if ($wantApexList.Count -eq 0 -and $wantWwwList.Count -eq 0) {
        $row.skipped = $true
        $results.Add([pscustomobject]$row) | Out-Null
        continue
    }

    if ($wantApexList.Count -gt 0) {
        $pub = @(Resolve-DnsName -Name $apex -Type A -ErrorAction SilentlyContinue | ForEach-Object {
                $ip = $_.PSObject.Properties['IPAddress']
                if ($null -ne $ip -and $null -ne $ip.Value) { [string]$ip.Value }
            } | Where-Object { $_ } | Select-Object -Unique)
        $row.apex_a_public = @($pub)
        $hitA = @($pub | Where-Object { $wantApexList -contains $_ })
        $row.apex_match = $hitA.Count -gt 0
    }

    if ($wantWwwList.Count -gt 0) {
        $w = "www.$apex"
        $pubW = @(Resolve-DnsName -Name $w -Type CNAME -ErrorAction SilentlyContinue | ForEach-Object {
                $nh = $_.PSObject.Properties['NameHost']
                if ($null -ne $nh -and $null -ne $nh.Value) { [string]$nh.Value.TrimEnd('.') }
            } | Select-Object -Unique)
        $row.www_cname_public = @($pubW)
        $wantLower = @($wantWwwList | ForEach-Object { $_.ToLowerInvariant() })
        $hitW = @($pubW | Where-Object { $wantLower -contains $_.ToLowerInvariant() })
        if ($hitW.Count -gt 0) {
            $row.www_match = $true
            $row.www_match_mode = "cname"
        }
        else {
            $pubWwwA = @(Resolve-DnsName -Name $w -Type A -ErrorAction SilentlyContinue | ForEach-Object {
                    $ip = $_.PSObject.Properties['IPAddress']
                    if ($null -ne $ip -and $null -ne $ip.Value) { [string]$ip.Value }
                } | Where-Object { $_ } | Select-Object -Unique)
            $row.www_a_public = @($pubWwwA)
            $targetIps = [System.Collections.Generic.List[string]]::new()
            foreach ($t in $wantWwwList) {
                $ips = @(Resolve-DnsName -Name $t -Type A -ErrorAction SilentlyContinue | ForEach-Object {
                        $ip = $_.PSObject.Properties['IPAddress']
                        if ($null -ne $ip -and $null -ne $ip.Value) { [string]$ip.Value }
                    } | Where-Object { $_ } | Select-Object -Unique)
                foreach ($ip in $ips) { $targetIps.Add($ip) | Out-Null }
            }
            $uniqTargets = @($targetIps | Select-Object -Unique)
            $hitViaA = @($pubWwwA | Where-Object { $uniqTargets -contains $_ })
            if ($hitViaA.Count -gt 0) {
                $row.www_match = $true
                $row.www_match_mode = "flattened_a"
            }
            else {
                $row.www_match = $false
                $row.www_match_mode = "cname_or_a_mismatch"
            }
        }
    }

    $results.Add([pscustomobject]$row) | Out-Null
}

$payload = [ordered]@{
    schema               = "hostinger_exit_rollback_rehearsal_v1"
    generated_at_utc     = [datetime]::UtcNow.ToString("o")
    template_path        = $TemplateJson
    rows                 = @($results)
    all_skipped_or_match = -not @($results | Where-Object {
            (-not $_.skipped) -and (
                ($null -ne $_.apex_match -and -not $_.apex_match) -or
                ($null -ne $_.www_match -and -not $_.www_match)
            )
        }).Count
}

$dir = Split-Path -Parent $OutJson
if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
($payload | ConvertTo-Json -Depth 10) | Set-Content -LiteralPath $OutJson -Encoding UTF8
Write-Host "Wrote $OutJson" -ForegroundColor Green
Write-Host ($payload | ConvertTo-Json -Compress -Depth 4)

exit 0
