#Requires -Version 5.1
param()

$ErrorActionPreference = "Stop"

$paths = @(
    "F:\workspace_archive",
    "G:\공유 드라이브\MKM_DATA_VAULT\archive\MKM_ARCHIVE_FROM_F\workspace_archive"
)

Write-Host "[INFO] Adding Defender exclusions..." -ForegroundColor Cyan
foreach ($p in $paths) {
    if (-not (Test-Path -LiteralPath $p)) {
        Write-Warning "Path not found (still adding anyway): $p"
    }
    Add-MpPreference -ExclusionPath $p
    Write-Host "[OK] Added exclusion: $p" -ForegroundColor Green
}

$applied = Get-MpPreference | Select-Object -ExpandProperty ExclusionPath
Write-Host "`n[INFO] Current exclusion paths:" -ForegroundColor Cyan
$applied | ForEach-Object { Write-Host " - $_" }

Write-Host "`n[DONE] Defender exclusions updated." -ForegroundColor Green
