#Requires -Version 5.1
<#
.SYNOPSIS
  OpenData 327 — official 붙임2 HWPX auto-fill + Hancom resave + Downloads copy + PDF export.
#>
param(
    [string]$TemplateHwpx = "",
    [switch]$SkipHancom,
    [switch]$SkipPdfPrep
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$downloadsTemplate = Join-Path $env:USERPROFILE "Downloads\(붙임2) 『AI+ OpenData 챌린지』 사업계획서 양식.hwpx"
$inboxTemplate = Join-Path $root "data\btrack\hwpx_poc\inbox\opendata_327_official_business_plan_v1.hwpx"
$slotsJson = Join-Path $root "data\btrack\hwpx_poc\slots_opendata_327_official_v1.json"
$filledOut = Join-Path $root "reports\opendata_327_official_filled_v4.hwpx"
$filledPdf = Join-Path $root "reports\opendata_327_official_filled_v4.pdf"
$dlHwpx = Join-Path $env:USERPROFILE "Downloads\(붙임2)_AI+OpenData_사업계획서_목소리_채움본.hwpx"
$dlPdf = Join-Path $env:USERPROFILE "Downloads\(붙임2)_AI+OpenData_사업계획서_목소리_제출용.pdf"

if (-not $TemplateHwpx) {
    if (Test-Path -LiteralPath $downloadsTemplate) { $TemplateHwpx = $downloadsTemplate }
    elseif (Test-Path -LiteralPath $inboxTemplate) { $TemplateHwpx = $inboxTemplate }
    else { $TemplateHwpx = $downloadsTemplate }
}
if (-not (Test-Path -LiteralPath $TemplateHwpx)) {
    Write-Error "HWPX template not found: $TemplateHwpx"
}

Write-Host "== Build slots from SSOT ==" -ForegroundColor Cyan
py scripts/build_opendata_327_hwpx_slots_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== Fill official 붙임2 HWPX ==" -ForegroundColor Cyan
py scripts/fill_hwpx_by_label_cells_v1.py `
    --hwpx $TemplateHwpx `
    --slots-json $slotsJson `
    --out $filledOut `
    --report-json reports/opendata_327_hwpx_fill_latest.json
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== G5: blue notice strip + black charPr ==" -ForegroundColor Cyan
$filledG5 = Join-Path $root "reports\opendata_327_official_filled_g5_v1.hwpx"
py scripts/normalize_hwpx_submit_g5_v1.py --hwpx-in $filledOut --hwpx-out $filledG5 `
    --report-json reports/opendata_327_hwpx_g5_normalize_latest.json
if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $filledG5)) {
    Copy-Item -LiteralPath $filledG5 -Destination $filledOut -Force
} else {
    Write-Warning "G5 normalize failed — open Hancom and delete blue ※ blocks manually"
}

if (-not $SkipHancom) {
    Write-Host "== Hancom resave (cell text visible) ==" -ForegroundColor Cyan
    $hancomRoundtrip = Join-Path $root "reports\opendata_327_official_filled_hancom_v1.hwpx"
    py scripts/resave_hwpx_via_hancom_v1.py --hwpx $filledOut --out-hwpx $hancomRoundtrip
    if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $hancomRoundtrip)) {
        Copy-Item -LiteralPath $hancomRoundtrip -Destination $filledOut -Force
    } else {
        Write-Warning "Hancom resave skipped/failed — open $filledOut in Hancom and verify cells"
    }
}

Copy-Item -LiteralPath $filledOut -Destination $dlHwpx -Force
Write-Host "Downloads HWPX: $dlHwpx" -ForegroundColor Green

if (-not $SkipPdfPrep) {
    Write-Host "== PDF bundle (K-Startup upload fallback) ==" -ForegroundColor Cyan
    & (Join-Path $root "scripts\Run-OpenData327SubmissionPrep_v1.ps1")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $bcd = Join-Path $root "reports\opendata_327_submission_bcd_merged_v1.pdf"
    if (Test-Path -LiteralPath $bcd) {
        Copy-Item -LiteralPath $bcd -Destination $dlPdf -Force
        Write-Host "Downloads PDF (B+C+D merged): $dlPdf" -ForegroundColor Green
    }
}

Write-Host "[DONE] official HWPX filled + copied to Downloads" -ForegroundColor Green
Write-Host "K-Startup T1069: open Hancom -> PDF 저장 -> upload (or use merged PDF if 양식 검수 OK)" -ForegroundColor Yellow
