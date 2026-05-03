param(
    [string]$WorkDir = ".",
    [double]$PerRunCapUsd = 0.50,
    [int]$MaxImages = 2
)

$ErrorActionPreference = "Stop"

function Write-Section([string]$title) {
    Write-Host ""
    Write-Host "=== $title ===" -ForegroundColor Cyan
}

function Get-RegexPatterns {
    @(
        "\uC218\uC775\s*\uBCF4\uC7A5|\uBB34\uC870\uAC74\s*\uC218\uC775|\uD655\uC2E4\uD55C\s*\uC218\uC775|\uD655\uC815\s*\uC218\uC775",
        "\uC6D0\uAE08\s*\uBCF4\uC7A5|\uC190\uC2E4\s*\uC5C6\uC74C|\uC190\uC2E4\s*\uC81C\uB85C|\uBB34\uC704\uD5D8|\uD544\uC2B9",
        "\uB9E4\uC218\s*\uC2E0\uD638|\uB9E4\uB3C4\s*\uC2E0\uD638|\uD22C\uC790\s*\uC790\uBB38",
        "guaranteed[- ]?(profit|return|returns)",
        "risk[- ]?free\s*returns?|no\s*downside|no\s*loss|zero\s*risk",
        "capital\s*guaranteed|sure[- ]?win|certain\s*gains",
        "investment\s*advice|trading\s*signal"
    )
}

function Scan-Text([string]$Text, [string]$SourceName) {
    $patterns = Get-RegexPatterns
    $hits = @()
    foreach ($pat in $patterns) {
        $matches = [regex]::Matches($Text, $pat, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        foreach ($m in $matches) {
            $hits += [pscustomobject]@{
                source = $SourceName
                value  = $m.Value
                index  = $m.Index
                pattern = $pat
            }
        }
    }
    return $hits
}

Write-Section "Track C Preflight Prompts"
$preflight = @'
Auto Safe Mode ON: apply compliance and cost guardrails automatically; proceed without extra prompts when <=`$0.50 and <=2 images; ask only if limits would be exceeded.
Track C compliance lock ON: no investment advice, no guaranteed returns/profit, no risk-free wording, regex preflight must return zero hits before final output.
Cost gate ON: monthly cap `$5, per-run cap `$0.50, max 2 images (hard max 4), stop if estimate exceeds cap.
'@
Write-Host $preflight

$resolvedWorkDir = Resolve-Path $WorkDir
$campaignBrief = Join-Path $resolvedWorkDir "campaign-brief.md"
$manifestPath = Join-Path $resolvedWorkDir "generation-manifest.json"
$bananaCosts = Join-Path $env:USERPROFILE ".banana/costs.json"

Write-Section "Compliance Check"
if (Test-Path $campaignBrief) {
    $content = Get-Content -Raw -Encoding UTF8 $campaignBrief
    $hits = Scan-Text -Text $content -SourceName "campaign-brief.md"
    if ($hits.Count -eq 0) {
        Write-Host "PASS: prohibited-phrase hits = 0" -ForegroundColor Green
    } else {
        Write-Host "FAIL: prohibited-phrase hits = $($hits.Count)" -ForegroundColor Red
        $hits | Select-Object -First 20 | ForEach-Object {
            Write-Host (" - [{0}] {1} @ {2}" -f $_.source, $_.value, $_.index)
        }
    }
} else {
    Write-Host "SKIP: campaign-brief.md not found in $resolvedWorkDir"
}

Write-Section "Cost/Image Gate"
$imageCount = 0
if (Test-Path $manifestPath) {
    $manifest = Get-Content -Raw -Encoding UTF8 $manifestPath | ConvertFrom-Json
    if ($null -ne $manifest.total_assets) {
        $imageCount = [int]$manifest.total_assets
    } elseif ($null -ne $manifest.assets) {
        $imageCount = @($manifest.assets).Count
    }
    Write-Host "Detected images from generation-manifest.json: $imageCount"
} else {
    $pngs = Get-ChildItem -Path (Join-Path $resolvedWorkDir "ad-assets") -Recurse -File -Filter *.png -ErrorAction SilentlyContinue
    $imageCount = @($pngs).Count
    if ($imageCount -gt 0) {
        Write-Host "Detected images from ad-assets/*.png: $imageCount"
    } else {
        Write-Host "SKIP: no generation-manifest.json or ad-assets/*.png found"
    }
}

if ($imageCount -gt 0) {
    if ($imageCount -le $MaxImages) {
        Write-Host "PASS: image count ($imageCount) <= max ($MaxImages)" -ForegroundColor Green
    } else {
        Write-Host "FAIL: image count ($imageCount) > max ($MaxImages)" -ForegroundColor Red
    }
}

$runCost = $null
if (Test-Path $bananaCosts) {
    try {
        $costObj = Get-Content -Raw -Encoding UTF8 $bananaCosts | ConvertFrom-Json
        if ($null -ne $costObj.total_usd) {
            $runCost = [double]$costObj.total_usd
        } elseif ($null -ne $costObj.total) {
            $runCost = [double]$costObj.total
        }
    } catch {
        Write-Host "WARN: could not parse $bananaCosts"
    }
}

if ($null -ne $runCost) {
    Write-Host ("Detected cumulative cost (from .banana/costs.json): ${0:N2}" -f $runCost)
    if ($runCost -le $PerRunCapUsd) {
        Write-Host ("PASS: cost ${0:N2} <= per-run cap ${1:N2}" -f $runCost, $PerRunCapUsd) -ForegroundColor Green
    } else {
        Write-Host ("WARN: cost ${0:N2} > per-run cap ${1:N2} (check run window/counters)" -f $runCost, $PerRunCapUsd) -ForegroundColor Yellow
    }
} else {
    Write-Host "SKIP: cost data not available in .banana/costs.json"
}

Write-Section "Next Manual Command Block"
Write-Host @'
/ads create

Context:
- Business type: b2b-enterprise
- Product: Enterprise Macro Risk Warning Brief
- Goal: leads/demos
- Platforms: LinkedIn, Google
- Monthly ad budget: $300
- Concepts requested: 3

Hard constraints:
- No investment advice wording
- No guaranteed return/profit wording
- No risk-free wording
- Educational and risk-aware tone only
'@
