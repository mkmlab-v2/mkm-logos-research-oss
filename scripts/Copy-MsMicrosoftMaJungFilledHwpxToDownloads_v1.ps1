#Requires -Version 5.1
<#
.SYNOPSIS
  Copy refilled ms_microsoft_ma_jung HWPX to Downloads with a stable Korean filename.
#>
param(
    [string]$Source = "",
    [string]$Dest = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not $Source) {
    $Source = Join-Path $root "reports\hwpx_poc\ms_microsoft_ma_jung_filled_v1.hwpx"
}
if (-not $Dest) {
    # ASCII filename avoids Copy-Item "Illegal characters in path" on some Windows locales.
    $Dest = Join-Path $env:USERPROFILE "Downloads\MKM_ms_microsoft_ma_jung_filled_v1.hwpx"
}
if (-not (Test-Path -LiteralPath $Source)) {
    Write-Error "Source missing: $Source — run Run-MsMicrosoftMaJungBusinessPlanHwpx_v1.ps1 first"
}
$dl = Join-Path $env:USERPROFILE "Downloads"
Copy-Item -LiteralPath $Source -Destination $Dest -Force
# Korean filenames — extension must include the dot (.hwpx / .hwp)
$koHwpx = Join-Path $dl "별첨1-2_마중_사업계획서_MKM_공고329.hwpx"
$koHwp = Join-Path $dl "별첨1-2_마중_사업계획서_MKM_공고329.hwp"
$hwpSrc = Join-Path $root "reports\hwpx_poc\ms_microsoft_ma_jung_filled_v1.hwp"
py -c "import shutil; from pathlib import Path; shutil.copy2(Path(r'''$Source'''), Path(r'''$koHwpx''')); h=Path(r'''$hwpSrc'''); shutil.copy2(h, Path(r'''$koHwp''')) if h.is_file() else None"
Write-Host "[DONE] $Dest" -ForegroundColor Green
if (Test-Path -LiteralPath $koHwpx) { Write-Host "[DONE] $koHwpx" -ForegroundColor Green }
if (Test-Path -LiteralPath $koHwp) { Write-Host "[DONE] $koHwp" -ForegroundColor Green }
Write-Host "Open in Hancom: T37 집행표 + 1-1/2-2 narrative (not ※ hint-only rows)." -ForegroundColor Yellow
