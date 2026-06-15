#Requires -Version 5.1
<#
.SYNOPSIS
  Copy compression pytest SSOT fixtures (lexicon pointer + production lexicon) into a worktree.

.DESCRIPTION
  B2B shard JSON lives under codebook/shards/b2b/ (git-tracked).
  Lexicon rail artifacts are gitignored (large); clone/worktree pytest needs a one-time sync
  from a machine that already has reports/constitution/btrack_pilot/ populated.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Sync-CompressionWorktreeFixtures_v1.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Sync-CompressionWorktreeFixtures_v1.ps1 `
    -SourceRoot C:\workspace -DestRoot C:\workspace\_pr_sasang_promotion
#>
param(
    [string]$SourceRoot = "C:\workspace",
    [string]$DestRoot = "",
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
if (-not $DestRoot) {
    $DestRoot = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { "C:\workspace" }
}

$relPilot = "reports/constitution/btrack_pilot"
$pointerName = "master_codebook_bench_lexicon_pointer_v1_latest.json"
$srcPilot = Join-Path $SourceRoot $relPilot
$dstPilot = Join-Path $DestRoot $relPilot
$srcPointer = Join-Path $srcPilot $pointerName

if (-not (Test-Path -LiteralPath $srcPointer)) {
    Write-Error "Missing source pointer: $srcPointer"
}

if (-not $WhatIfOnly) {
    New-Item -ItemType Directory -Path $dstPilot -Force | Out-Null
}

function Copy-IfSourceExists([string]$src, [string]$dst) {
    if (-not (Test-Path -LiteralPath $src)) {
        Write-Warning "Skip (missing source): $src"
        return $false
    }
    if ($WhatIfOnly) {
        Write-Host "[WhatIf] copy $src -> $dst"
        return $true
    }
    Copy-Item -LiteralPath $src -Destination $dst -Force
    Write-Host "OK: $dst"
    return $true
}

$dstPointer = Join-Path $dstPilot $pointerName
Copy-IfSourceExists $srcPointer $dstPointer | Out-Null

$pointerDoc = Get-Content -LiteralPath $srcPointer -Raw -Encoding UTF8 | ConvertFrom-Json
$prodRel = $pointerDoc.production_ssot.path
if (-not $prodRel) {
    Write-Error "production_ssot.path missing in pointer"
}

$srcLex = if ([System.IO.Path]::IsPathRooted($prodRel)) { $prodRel } else { Join-Path $SourceRoot $prodRel }
$dstLex = if ([System.IO.Path]::IsPathRooted($prodRel)) {
    Join-Path $DestRoot (Split-Path -Leaf $prodRel)
} else {
    Join-Path $DestRoot $prodRel
}

if (-not $WhatIfOnly) {
    $lexDir = Split-Path -Parent $dstLex
    if ($lexDir) { New-Item -ItemType Directory -Path $lexDir -Force | Out-Null }
}

if (-not (Copy-IfSourceExists $srcLex $dstLex)) {
    Write-Error "Production lexicon missing at source: $srcLex"
}

Write-Host "DONE: compression worktree fixtures synced (dest=$DestRoot)"
