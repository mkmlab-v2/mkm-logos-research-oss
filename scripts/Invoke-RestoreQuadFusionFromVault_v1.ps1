#Requires -Version 5.1
<#
.SYNOPSIS
  Restore quad_fusion_result JSON from MKM_DATA_VAULT into workspace data/quad_fusion_training.

  Vault SSOT (when mounted): G:\공유 드라이브\MKM_DATA_VAULT\projects\bitcoin-trading\data\quad_fusion_training
  Field snapshot default: quad_fusion_result_20260308_230751.json
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$VaultQuadDir = "G:\공유 드라이브\MKM_DATA_VAULT\projects\bitcoin-trading\data\quad_fusion_training",
    [string]$TargetName = "quad_fusion_result_20260308_230751.json",
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
$destDir = Join-Path $WorkspaceRoot "data\quad_fusion_training"
$destPath = Join-Path $destDir $TargetName

if (-not (Test-Path -LiteralPath $VaultQuadDir)) {
    Write-Error "Vault quad dir not found (mount G:): $VaultQuadDir"
}

$src = Join-Path $VaultQuadDir $TargetName
if (-not (Test-Path -LiteralPath $src)) {
    $latest = Get-ChildItem -LiteralPath $VaultQuadDir -Filter "quad_fusion_result_*.json" -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending |
        Select-Object -First 1
    if (-not $latest) {
        Write-Error "No quad_fusion_result_*.json in vault dir: $VaultQuadDir"
    }
    $src = $latest.FullName
    Write-Host "[quad-restore] exact name missing; using latest: $($latest.Name)" -ForegroundColor Yellow
}

if ($WhatIfOnly) {
    Write-Host "[quad-restore] WhatIf: copy $src -> $destPath"
    exit 0
}

if (-not (Test-Path -LiteralPath $destDir)) {
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
}
Copy-Item -LiteralPath $src -Destination $destPath -Force
Write-Host "[quad-restore] copied -> $destPath ($((Get-Item $destPath).Length) bytes)" -ForegroundColor Green

# Optional second canonical for btc regime map script
$altName = "quad_fusion_result_20260401_125917.json"
$altSrc = Join-Path $VaultQuadDir $altName
if ((Test-Path -LiteralPath $altSrc) -and $altName -ne (Split-Path $src -Leaf)) {
    Copy-Item -LiteralPath $altSrc -Destination (Join-Path $destDir $altName) -Force
    Write-Host "[quad-restore] copied -> $(Join-Path $destDir $altName)" -ForegroundColor Green
}

exit 0
