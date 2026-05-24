#Requires -Version 5.1
<#
.SYNOPSIS
  Recommended outer-lane follow-up: O-P5 zone inventory + CF apply + verify + personadiary probe.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-OuterLaneRecommendedFollowup_v1.ps1
#>
$ErrorActionPreference = "Stop"
$root = "C:\workspace"
Set-Location $root
$py = (Get-Command py -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "py" }

$warn = @()
function Step {
    param([string]$Name, [scriptblock]$Block, [switch]$WarnOnly)
    Write-Host "== $Name ==" -ForegroundColor Cyan
    & $Block
    $c = $LASTEXITCODE
    if ($c -ne 0) {
        if ($WarnOnly) {
            Write-Host "WARN $Name exit=$c" -ForegroundColor Yellow
            $script:warn += "$Name exit=$c"
            return
        }
        throw "$Name failed exit=$c"
    }
    Write-Host "OK $Name" -ForegroundColor Green
}

# 1) Zone inventory (writes list to stdout; jema12 id for fixture)
$invOut = Join-Path $root "reports\cloudflare_op5_zone_inventory_v1.json"
Step "cf_zone_inventory" -WarnOnly { & $py scripts/list_cloudflare_zones_for_op5_v1.py | Out-Null }

# 2) jema12 fixture zone_id from inventory
$jemaFixture = Join-Path $root "scripts\data\hostinger_full_exit\jema12_cloudflare_zone_v1.json"
if (Test-Path $invOut) {
    $inv = Get-Content $invOut -Raw | ConvertFrom-Json
    $pair = $inv.zones | Where-Object { $_[0] -eq "jema12.com" }
    if ($pair) {
        $fx = Get-Content $jemaFixture -Raw | ConvertFrom-Json
        $fx.zone_id = [string]$pair[1]
        $fx | ConvertTo-Json -Depth 4 | Set-Content $jemaFixture -Encoding UTF8
    }
}

# 3) O-P5 CF apply (trust zone-id)
$zid = (Get-Content $jemaFixture -Raw | ConvertFrom-Json).zone_id
if ($zid) {
    Step "op5_cf_studio_apply" -WarnOnly {
        & $py scripts/setup_cloudflare_jema12_studio_oracle_redirect_v1.py --zone-id $zid
    }
} else {
    $warn += "jema12 zone_id missing in fixture"
}

Step "op5_verify_jema12" { powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify_jema12_studio_oracle_redirect_v1.ps1 }

Step "personadiary_token_probe" -WarnOnly {
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-PersonadiaryCloudflareTokenProbe_v1.ps1
}

# 4) personadiary DNS only if dedicated token or probe ok
$probePath = Join-Path $root "reports\personadiary_cloudflare_token_probe_latest.json"
if (Test-Path $probePath) {
    $probe = Get-Content $probePath -Raw | ConvertFrom-Json
    if ($probe.ok) {
        Step "personadiary_dns_apply" -WarnOnly {
            powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-PersonadiaryCloudflareRoutingReadiness_v1.ps1 -Apply
        }
    } else {
        $pdLive = $false
        try {
            $h = & curl.exe -sSI --max-time 15 "https://personadiary.com/" 2>$null
            $pdLive = ($h | Select-String -Pattern '^HTTP/\S+\s+200' -Quiet)
        } catch { $pdLive = $false }
        if ($pdLive) {
            Write-Host "OK personadiary routing live (HTTP 200) — API dns_list 403 is automation-only" -ForegroundColor Green
        } else {
            $dedicated = [Environment]::GetEnvironmentVariable("MKM_CLOUDFLARE_PERSONADIARY_DNS_TOKEN", "User")
            if ($dedicated) {
                $env:CLOUDFLARE_API_TOKEN = $dedicated
                Step "personadiary_dns_apply_dedicated_token" -WarnOnly {
                    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-PersonadiaryCloudflareRoutingReadiness_v1.ps1 -Apply
                }
            } else {
                $warn += "personadiary not HTTP 200 and no DNS API token — dashboard or MKM_CLOUDFLARE_PERSONADIARY_DNS_TOKEN"
            }
        }
    }
}

Step "personadiary_v6_draft" { & $py scripts/build_personadiary_logos_oracle_sphere_v6_draft_v1.py }

$summary = @{
    schema = "outer_lane_recommended_followup_v1"
    completed_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    warnings = $warn
    artifacts = @(
        "reports/cloudflare_op5_zone_inventory_v1.json",
        "scripts/data/hostinger_full_exit/jema12_cloudflare_zone_v1.json",
        "reports/cloudflare_jema12_studio_oracle_redirect_latest.json",
        "reports/jema12_studio_oracle_redirect_check_latest.json",
        "reports/personadiary_cloudflare_token_probe_latest.json",
        "reports/outer_lane_followup_v1.json"
    )
}
$sumPath = Join-Path $root "reports\outer_lane_recommended_followup_latest.json"
$summary | ConvertTo-Json -Depth 6 | Set-Content $sumPath -Encoding UTF8
Write-Host "Wrote $sumPath"
if ($warn.Count) {
    Write-Host "DONE with warnings: $($warn -join '; ')" -ForegroundColor Yellow
    exit 0
}
Write-Host "DONE" -ForegroundColor Green
exit 0
