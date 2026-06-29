<#
.SYNOPSIS

  Post-deploy smoke for https://logos.jema-ai.com (workspace + docs URLs, per-page markers).



.EXAMPLE

  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify_logos_jema_ai_deploy_v1.ps1

#>

param(

    [string]$BaseUrl = "https://logos.jema-ai.com",

    [string]$OutJson = "reports/logos_jema_ai_deploy_verify_latest.json"

)



$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$base = $BaseUrl.TrimEnd("/")



$pageChecks = @(

    @{

        id      = "workspace"

        url     = "$base/logos-research"

        markers = @(

            "logos-research-page",

            "Cross-reference Graph",

            "Graph Studio",

            "Commercial beta",

            "research_only",

            "NON_GATING",

            "lr-meta-arch",

            "Cosmic Meta-Architecture",

            "data-logos-graph-studio-embed",

            "Logos Scripture Research"

        )

        forbidden = @("gematria_bridge_v1", "kernel_alignment", "Ei/Pf")

    }

    @{

        id      = "docs_hub"

        url     = "$base/logos-research/docs"

        markers = @(

            "logos-research-docs",

            "Logos Public Docs",

            "How it works",

            "Glossary",

            "send_gate: HOLD",

            "Not investment advice",

            "Open Graph Studio (live demo)"

        )

        forbidden = @()

    }

    @{

        id      = "docs_glossary"

        url     = "$base/logos-research/docs/glossary"

        markers = @(

            "logos-research-docs",

            "S-L-K-M",

            "Matching Layer",

            "Graph Studio",

            "send_gate",

            "Forbidden in public ads",

            "invisible core, visible evidence"

        )

        forbidden = @()

    }

    @{

        id      = "docs_faq"

        url     = "$base/logos-research/docs/faq"

        markers = @(

            "logos-research-docs",

            "send_gate: HOLD",

            "ready_for_external_send: false",

            "invisible core",

            "Not investment advice"

        )

        forbidden = @()

    }

)



function Test-LogosUrlMarkers {

    param(

        [string]$TargetUrl,

        [string[]]$MarkerList,

        [string[]]$ForbiddenList

    )

    $httpCode = & curl.exe -s -o NUL -w "%{http_code}" -L --max-time 45 $TargetUrl

    $tmp = Join-Path $env:TEMP ("logos-jema-ai-verify-{0}.html" -f ([guid]::NewGuid().ToString("n").Substring(0, 8)))

    & curl.exe -s -L --max-time 45 -o $tmp $TargetUrl | Out-Null

    $body = ""

    if (Test-Path $tmp) {

        $body = [System.IO.File]::ReadAllText($tmp, [System.Text.UTF8Encoding]::new($false))

        Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue

    }

    $found = @()

    $missing = @()

    foreach ($m in $MarkerList) {

        if ($body -and $body.Contains($m)) { $found += $m } else { $missing += $m }

    }

    $forbiddenHits = @()

    foreach ($f in $ForbiddenList) {

        if ($body -and $body.Contains($f)) { $forbiddenHits += $f }

    }

    return @{

        url              = $TargetUrl

        http_code        = [int]$httpCode

        markers_found    = $found

        markers_missing  = $missing

        forbidden_hits   = $forbiddenHits

        ok               = ($httpCode -eq "200") -and ($missing.Count -eq 0) -and ($forbiddenHits.Count -eq 0)

    }

}



$results = @()

foreach ($check in $pageChecks) {

    $results += (Test-LogosUrlMarkers -TargetUrl $check.url -MarkerList $check.markers -ForbiddenList $check.forbidden) | ForEach-Object {

        $_ | Add-Member -NotePropertyName id -NotePropertyValue $check.id -Force

        $_

    }

}



$ok = ($results | Where-Object { -not $_.ok }).Count -eq 0

$report = @{

    schema     = "logos_jema_ai_deploy_verify_v2"

    checked_at = (Get-Date).ToUniversalTime().ToString("o")

    base_url   = $base

    pages      = $results

    ok         = $ok

}



$outPath = Join-Path $root $OutJson

$dir = Split-Path $outPath -Parent

if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

$report | ConvertTo-Json -Depth 6 | Set-Content -Path $outPath -Encoding UTF8



if (-not $ok) {

    $miss = @()

    foreach ($r in $results) {

        if ($r.markers_missing.Count -gt 0) {

            $miss += ("{0}:missing={1}" -f $r.id, ($r.markers_missing -join "|"))

        }

        if ($r.forbidden_hits.Count -gt 0) {

            $miss += ("{0}:forbidden={1}" -f $r.id, ($r.forbidden_hits -join "|"))

        }

        if ($r.http_code -ne 200) {

            $miss += ("{0}:http={1}" -f $r.id, $r.http_code)

        }

    }

    Write-Host ("[logos-verify] FAIL {0}" -f ($miss -join "; ")) -ForegroundColor Red

    exit 1

}

Write-Host "[logos-verify] OK workspace+docs (4 URLs) report=$outPath" -ForegroundColor Green

exit 0

