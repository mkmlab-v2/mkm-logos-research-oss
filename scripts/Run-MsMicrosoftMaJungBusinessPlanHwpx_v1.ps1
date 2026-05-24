#Requires -Version 5.1
<#
.SYNOPSIS
  Microsoft ma-jung program business plan .hwp -> .hwpx + slot fill (B-track).
.PARAMETER HwpPath
  Source .hwp (default: Downloads copy or inbox).
.PARAMETER SlotsJson
  Slot mapping JSON.
#>
param(
    [string]$HwpPath = "",
    [string]$SlotsJson = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$inbox = Join-Path $root "data\btrack\hwpx_poc\inbox"
$defaultHwp = Join-Path $inbox "ms_microsoft_ma_jung_program_business_plan_v1.hwp"
$defaultHwpx = Join-Path $inbox "ms_microsoft_ma_jung_program_business_plan_v1.hwpx"
$defaultSlots = Join-Path $root "data\btrack\hwpx_poc\slots_ms_microsoft_ma_jung_v1.json"
$defaultSlotsExample = Join-Path $root "data\btrack\hwpx_poc\slots_ms_microsoft_ma_jung_v1.example.json"
$filledOut = Join-Path $root "reports\hwpx_poc\ms_microsoft_ma_jung_filled_v1.hwpx"
$downloadsDefault = Join-Path $env:USERPROFILE "Downloads\별첨1-2. (마이크로소프트) 마중 프로그램 사업계획서.hwp"

if (-not $HwpPath) {
    if (Test-Path -LiteralPath $defaultHwp) { $HwpPath = $defaultHwp }
    elseif (Test-Path -LiteralPath $downloadsDefault) { $HwpPath = $downloadsDefault }
    else { $HwpPath = $defaultHwp }
}
if (-not $SlotsJson) { $SlotsJson = $defaultSlots }

if (-not (Test-Path -LiteralPath $HwpPath)) {
    Write-Error "HWP not found: $HwpPath"
}

if (-not (Test-Path -LiteralPath $defaultHwpx)) {
    Write-Host "== Convert HWP -> HWPX (Hancom COM) ==" -ForegroundColor Cyan
    py scripts/convert_hwp_to_hwpx_hancom_v1.py --meta-json reports/hwpx_poc/convert_ms_microsoft_ma_jung_latest.json $HwpPath --out $defaultHwpx
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "== Build slots from MS paste SSOT ==" -ForegroundColor Cyan
py scripts/build_ms_microsoft_ma_jung_slots_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if (-not $SlotsJson) { $SlotsJson = $defaultSlots }
if (-not (Test-Path -LiteralPath $SlotsJson) -and (Test-Path -LiteralPath $defaultSlotsExample)) {
    $SlotsJson = $defaultSlotsExample
}

Write-Host "== Fill HWPX from slots ==" -ForegroundColor Cyan
py scripts/fill_hwpx_by_label_cells_v1.py --hwpx $defaultHwpx --slots-json $SlotsJson --out $filledOut
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== Resave .hwp + copy to Downloads (submission) ==" -ForegroundColor Cyan
py scripts/resave_hwpx_via_hancom_v1.py --hwpx $filledOut --copy-downloads
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/audit_ms_ma_jung_hwpx_v1.py --hwpx (Join-Path $env:USERPROFILE "Downloads\별첨1-2_마중_사업계획서_MKM_공고329.hwpx")
if ($LASTEXITCODE -ne 0) { Write-Warning "audit exit $LASTEXITCODE — review reports/hwpx_poc/ms_ma_jung_hwpx_audit_latest.json" }

Write-Host "[DONE] $filledOut" -ForegroundColor Green
Write-Host "Downloads: $env:USERPROFILE\Downloads\별첨1-2_마중_사업계획서_MKM_공고329.hwp" -ForegroundColor Green
