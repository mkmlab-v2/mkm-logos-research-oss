#Requires -Version 5.1
<#
.SYNOPSIS
  Verifies the three canonical GO-bundle JSON files exist under docs/final/artifacts/.
  Exit 0 if all present; non-zero if any missing.
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$manifest = Join-Path $root "docs\final\artifacts\war_prolongation_go_bundle_manifest_v1.json"
if (-not (Test-Path -LiteralPath $manifest)) {
    Write-Error "Manifest not found: $manifest"
    exit 2
}
$j = Get-Content -LiteralPath $manifest -Raw -Encoding UTF8 | ConvertFrom-Json
$missing = @()
foreach ($a in $j.artifacts) {
    $p = Join-Path $root ($a.path -replace "/", "\")
    if (-not (Test-Path -LiteralPath $p)) {
        $missing += $a.path
    }
}
if ($missing.Count -gt 0) {
    Write-Host "MISSING:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  $_" }
    exit 1
}
Write-Host "OK: all GO-bundle artifacts present." -ForegroundColor Green
exit 0
