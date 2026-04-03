<#
.SYNOPSIS
  Regenerates v23 evaluation bundle (default-extra), NotebookLM MD mirror, and optionally mirrors to G: vault.

.EXAMPLE
  pwsh -File scripts/Invoke-LogosKospiShadowNotebooklmBundle.ps1
.EXAMPLE
  pwsh -File scripts/Invoke-LogosKospiShadowNotebooklmBundle.ps1 -SyncVault
#>
param(
    [string]$WorkspaceRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$SyncVault
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

Write-Host "==> report_logos_shadow_evaluation_bundle_v23.py (default EXTRA)"
py scripts/report_logos_shadow_evaluation_bundle_v23.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> regen_logos_kospi_shadow_v23_notebooklm_md.py"
py scripts/regen_logos_kospi_shadow_v23_notebooklm_md.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($SyncVault) {
    Write-Host "==> sync_notebooklm_sources_to_mkm_data_vault.ps1"
    & pwsh -NoProfile -File (Join-Path $WorkspaceRoot "scripts\sync_notebooklm_sources_to_mkm_data_vault.ps1")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "OK: v23_latest.json + logos_kospi_shadow_evaluation_bundle_v23_notebooklm.md"
exit 0
