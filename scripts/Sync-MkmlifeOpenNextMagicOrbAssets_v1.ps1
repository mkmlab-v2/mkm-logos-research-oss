# Sync mkmlife public Magic Orb JSON into .open-next/assets (required before -SkipBuild deploy).
param(
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

$root = "projects\mkm\mkm-life"
$pairs = @(
    @{
        Src = Join-Path $root "public\data\magic_orb_question_insight_v1_latest.json"
        Dst = Join-Path $root ".open-next\assets\data\magic_orb_question_insight_v1_latest.json"
    },
    @{
        SrcDir = Join-Path $root "public\data\magic_orb_insight_by_query"
        DstDir = Join-Path $root ".open-next\assets\data\magic_orb_insight_by_query"
    }
)

$copied = 0
if ($pairs[0].Src -and (Test-Path -LiteralPath $pairs[0].Src)) {
    $dstDir = Split-Path -Parent $pairs[0].Dst
    if (-not $WhatIfOnly) { New-Item -ItemType Directory -Force -Path $dstDir | Out-Null }
    if ($WhatIfOnly) {
        Write-Host "[whatif] $($pairs[0].Src) -> $($pairs[0].Dst)"
    } else {
        Copy-Item -LiteralPath $pairs[0].Src -Destination $pairs[0].Dst -Force
        $copied++
    }
}

$srcDir = $pairs[1].SrcDir
$dstDir = $pairs[1].DstDir
if (Test-Path -LiteralPath $srcDir) {
    if (-not $WhatIfOnly) { New-Item -ItemType Directory -Force -Path $dstDir | Out-Null }
    Get-ChildItem -LiteralPath $srcDir -Filter "*.json" | ForEach-Object {
        $dest = Join-Path $dstDir $_.Name
        if ($WhatIfOnly) {
            Write-Host "[whatif] $($_.FullName) -> $dest"
        } else {
            Copy-Item -LiteralPath $_.FullName -Destination $dest -Force
            $copied++
        }
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $root ".open-next\assets"))) {
    Write-Warning "Missing .open-next/assets — run full Deploy-CloudflareMkmlife.ps1 build once first."
    exit 1
}

Write-Host "[OK] synced $copied magic orb asset file(s) -> .open-next/assets" -ForegroundColor Green
