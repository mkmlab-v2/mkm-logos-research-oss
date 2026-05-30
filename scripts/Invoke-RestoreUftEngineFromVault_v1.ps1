#Requires -Version 5.1
<#
.SYNOPSIS
  Restore UnifiedFieldTheoryEngine (+ dna_complement_4d) from MKM_DATA_VAULT into tools/core.

  Requires MKM_DATA_VAULT_ROOT or -VaultToolsCoreDir.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$VaultToolsCoreDir = "",
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($VaultToolsCoreDir)) {
    if ([string]::IsNullOrWhiteSpace($env:MKM_DATA_VAULT_ROOT)) {
        Write-Error "Set MKM_DATA_VAULT_ROOT or pass -VaultToolsCoreDir."
    }
    $VaultToolsCoreDir = Join-Path $env:MKM_DATA_VAULT_ROOT "projects\bitcoin-trading\tools\core"
}

$dest = Join-Path $WorkspaceRoot "tools\core"
$files = @(
    "unified_field_theory_engine.py",
    "unified_field_theory_engine_gpu.py",
    "dna_complement_4d.py"
)

if (-not (Test-Path -LiteralPath $VaultToolsCoreDir)) {
    Write-Error "Vault tools/core not found: $VaultToolsCoreDir"
}

if ($WhatIfOnly) {
    foreach ($f in $files) {
        Write-Host "[uft-restore] WhatIf: $(Join-Path $VaultToolsCoreDir $f) -> $(Join-Path $dest $f)"
    }
    exit 0
}

if (-not (Test-Path -LiteralPath $dest)) {
    New-Item -ItemType Directory -Path $dest -Force | Out-Null
}

foreach ($f in $files) {
    $src = Join-Path $VaultToolsCoreDir $f
    if (-not (Test-Path -LiteralPath $src)) {
        Write-Warning "skip missing vault file: $f"
        continue
    }
    Copy-Item -LiteralPath $src -Destination (Join-Path $dest $f) -Force
    Write-Host "[uft-restore] copied $f" -ForegroundColor Green
}

exit 0
