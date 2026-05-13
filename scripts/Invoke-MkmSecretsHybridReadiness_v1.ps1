#Requires -Version 5.1
<#
.SYNOPSIS
  Hybrid secret readiness: repo hygiene + (Windows) DPAPI store smoke.

.DESCRIPTION
  1. Verify-MonorepoSecretHygiene.ps1 (exit 1 if .env tracked / not gitignored).
  2. Windows only: report whether %APPDATA%\MKM\secret_store_v1.json exists and key count (names only, no values).
  3. Non-Windows: print VPS pointer only (systemd /etc/mkm env template).

  Does not set secrets. SSOT: docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md (비밀 키 절).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmSecretsHybridReadiness_v1.ps1
#>
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$hygiene = Join-Path $RepoRoot "scripts\Verify-MonorepoSecretHygiene.ps1"
if (-not (Test-Path -LiteralPath $hygiene)) {
    throw "Missing: $hygiene"
}
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $hygiene -RepoRoot $RepoRoot
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "=== Hybrid secret readiness (MKM) ===" -ForegroundColor Cyan

$isWindowsHost = ($PSVersionTable.PSVersion.Major -ge 6 -and $IsWindows) -or ($env:OS -like '*Windows*')
if ($isWindowsHost) {
    $storeDir = Join-Path $env:APPDATA "MKM"
    $storePath = Join-Path $storeDir "secret_store_v1.json"
    if (-not (Test-Path -LiteralPath $storePath)) {
        Write-Host "[info] DPAPI store not created yet: $storePath" -ForegroundColor Yellow
        Write-Host "       When needed: scripts\Invoke-EncryptedSecretStore.ps1 -Action set -Key KEYNAME -Value SECRET"
    }
    else {
        Write-Host "[ok] DPAPI store present: $storePath" -ForegroundColor Green
        $inv = Join-Path $RepoRoot "scripts\Invoke-EncryptedSecretStore.ps1"
        if (Test-Path -LiteralPath $inv) {
            $names = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $inv -Action list 2>$null
            if ($null -eq $names) { $names = @() }
            $arr = @($names | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
            Write-Host "       Stored key count (names only): $($arr.Count)"
            if ($arr.Count -eq 0) {
                Write-Host "       [info] Store file exists but has no keys yet." -ForegroundColor Yellow
            }
        }
    }
    Write-Host "       Bridge (PoC): scripts\security_agent_manager.py - see CONSTITUTION 1.1.2 (Security Agent)."
}
else {
    Write-Host "[info] Non-Windows host: use repo-outside env file or systemd EnvironmentFile path." -ForegroundColor Yellow
    Write-Host "       Template: scripts/deploy/linux/mkm-monorepo-vps.env.example"
    Write-Host "       SSOT: docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md (비밀 키 절)."
}

Write-Host ""
Write-Host "Invoke-MkmSecretsHybridReadiness_v1: OK (exit 0)" -ForegroundColor Green
exit 0
