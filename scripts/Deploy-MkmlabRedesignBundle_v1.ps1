# Zip mkmlab-redesign for manual upload backup. Primary deploy: Sync-MkmlabRedesignToVps_v1.ps1 (Hostinger VPS + Cloudflare DNS).
param(
    [string]$SourceDir = "",
    [string]$OutZip = ""
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not $SourceDir) { $SourceDir = Join-Path $root "mkmlab-redesign" }
if (-not $OutZip) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $OutZip = Join-Path $root "reports\mkmlab-redesign_$stamp.zip"
}
if (-not (Test-Path $SourceDir)) {
    Write-Error "Missing source: $SourceDir"
}
$outDir = Split-Path -Parent $OutZip
if ($outDir -and -not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
if (Test-Path $OutZip) { Remove-Item -Force $OutZip }
Compress-Archive -Path (Join-Path $SourceDir "*") -DestinationPath $OutZip -CompressionLevel Optimal
Write-Host "[mkmlab-deploy-bundle] OK: $OutZip"
Write-Host "[mkmlab-deploy-bundle] Deploy: scripts/Sync-MkmlabRedesignToVps_v1.ps1 -> VPS web root; Cloudflare DNS -> VPS (not hPanel public_html)."
exit 0
