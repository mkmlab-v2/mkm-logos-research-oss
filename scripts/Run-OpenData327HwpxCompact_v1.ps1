#Requires -Version 5.1
<#
.SYNOPSIS
  OpenData 327 — Hancom(pyhwpx) spacing compact for user-edited HWPX.
#>
param(
    [string]$HwpxIn = "",
    [switch]$Visible
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $HwpxIn) {
    $HwpxIn = Join-Path $env:USERPROFILE "Downloads\(붙임2)_AI+OpenData_사업계획서_목소리_채움본.hwpx"
}
$out = Join-Path $root "reports\opendata_327_official_filled_v4_compact.hwpx"
$argsPy = @(
    "scripts/compact_opendata_327_hwpx_hancom_v1.py",
    "--hwpx-in", $HwpxIn,
    "--hwpx-out", $out,
    "--report-json", "reports/opendata_327_hwpx_compact_latest.json"
)
if ($Visible) { $argsPy += "--visible" }
py @argsPy
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Copy-Item -LiteralPath $out -Destination $HwpxIn -Force
Write-Host "Compact HWPX saved: $out" -ForegroundColor Green
Write-Host "Downloads copy updated: $HwpxIn" -ForegroundColor Green
