#Requires -Version 5.1

<#

.SYNOPSIS

  O-P5 gate: jema12.com /studio -> jemaai.cloud Oracle v6 (canonical non-www).

  Also checks www.jema12.com (known misroute to jema-ai.com until CF www rule is applied).

  Writes reports/jema12_studio_oracle_redirect_check_latest.json

#>

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

$out = Join-Path $root "reports\jema12_studio_oracle_redirect_check_latest.json"

$targetSubstr = "public_showroom_logos_oracle_v6.html"

$canonicalBase = if ($env:BASE_URL) { $env:BASE_URL.TrimEnd('/') } else { "https://jema12.com" }



function Get-RedirectChain {

    param([string]$Url)

    $chain = @()

    $u = $Url

    for ($i = 0; $i -lt 8; $i++) {

        $hdr = & curl.exe -sSI --max-time 25 $u 2>$null

        if ($LASTEXITCODE -ne 0) { return @{ ok = $false; chain = $chain; error = "curl failed" } }

        $statusLine = ($hdr | Select-String -Pattern '^HTTP/' | Select-Object -Last 1).ToString()
        $code = $statusLine -replace '^HTTP/\S+\s+', ''
        $statusNum = if ($code -match '^(\d{3})') { $Matches[1] } else { $code }

        $loc = ($hdr | Select-String -Pattern '^location:' -CaseSensitive:$false | Select-Object -Last 1)

        $locVal = if ($loc) { ($loc -replace '(?i)^location:\s*', '').Trim() } else { $null }

        $chain += @{ url = $u; status = $code.Trim(); location = $locVal }

        if ($statusNum -match '^(301|302|303|307|308)$' -and $locVal) {

            if ($locVal -match '^https?://') { $u = $locVal } else {

                $uri = [Uri]$u

                $u = ($uri.GetLeftPart([UriPartial]::Authority).TrimEnd('/') + '/' + $locVal.TrimStart('/'))

            }

            continue

        }

        break

    }

    $final = $chain[-1]

    $hitLocation = ($chain | ForEach-Object { $_.location } | Where-Object { $_ -and $_ -like "*$targetSubstr*" }) -ne $null
    $hitFinal = ($final.url -like "*$targetSubstr*")
    $hit = $hitLocation -or $hitFinal

    $badJemaAi = ($chain | ForEach-Object { $_.location } | Where-Object {
            $_ -and ($_ -like "*jema-ai.com*" -or $_ -like "*app.jema-ai.com*")
        }) -ne $null

    return @{
        ok           = $hit
        chain        = $chain
        final_url    = $final.url
        final_status = $final.status
        misroute_jema_ai = $badJemaAi -and -not $hit
        end_to_end_v6  = $hitFinal
    }

}



$rStudio = Get-RedirectChain "$canonicalBase/studio"

$rStudioSlash = Get-RedirectChain "$canonicalBase/studio/"

$rWww = Get-RedirectChain "https://www.jema12.com/studio"



$doc = @{

    schema           = "jema12_studio_oracle_redirect_check_v1"

    checked_at_utc   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

    canonical_base   = $canonicalBase

    target_substr    = $targetSubstr

    studio           = $rStudio

    studio_slash     = $rStudioSlash

    www_studio       = $rWww

    op5_pass         = ($rStudio.ok -or $rStudioSlash.ok)

    www_studio_pass  = $rWww.ok
    www_end_to_end_v6 = $rWww.end_to_end_v6

    www_fix_required = -not $rWww.ok

    www_dashboard_hint = "reports/ms_rq019_paste_ready/op5_www_studio_redirect_manual.txt"

    apply_hint       = "reports/ms_rq019_paste_ready/op5_jema12_nginx_one_liner.txt"

    cf_api_cli       = "py scripts/setup_cloudflare_jema12_studio_oracle_redirect_v1.py --zone-id a9f34634593eef57609e48c3ffbe6f24"

}



New-Item -ItemType Directory -Force -Path (Split-Path $out) | Out-Null

$doc | ConvertTo-Json -Depth 10 | Set-Content -Path $out -Encoding UTF8



Write-Host "== jema12 studio -> oracle v6 ==" -ForegroundColor Cyan

Write-Host "canonical op5_pass=$($doc.op5_pass) base=$canonicalBase"

foreach ($step in $rStudio.chain) { Write-Host "  $($step.status) $($step.url) -> $($step.location)" }

Write-Host "www_studio_pass=$($doc.www_studio_pass)"

if ($doc.www_fix_required) {

    Write-Host "WARN www optional (O-P5 already pass) — op5_www_studio_redirect_manual.txt if you need www host" -ForegroundColor Yellow

    foreach ($step in $rWww.chain) { Write-Host "  www: $($step.status) $($step.url) -> $($step.location)" }

}



if (-not $doc.op5_pass) {

    Write-Host "EXIT 1 — canonical /studio must reach oracle v6" -ForegroundColor Red

    exit 1

}

if ($doc.www_fix_required) {

    Write-Host "EXIT 0 (canonical OK; www pending)" -ForegroundColor Yellow

    exit 0

}

Write-Host "EXIT 0 (canonical + www)" -ForegroundColor Green

exit 0

