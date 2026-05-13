<#
.SYNOPSIS
  Build per-lens NotebookLM source packs, then mirror Vault (best-effort).

.NOTES
  Google NotebookLM notebook creation still requires share URLs / web UI.
  This script automates everything that is local + deterministic.
#>
param(
  [string]$WorkspaceRoot = (Split-Path -Parent $PSScriptRoot),
  [switch]$SkipVaultMirror
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

Write-Host "==> build_notebooklm_lens_source_packs_v1.py" -ForegroundColor Cyan
py scripts/build_notebooklm_lens_source_packs_v1.py
if ($LASTEXITCODE -ne 0) { throw "lens packs exit $LASTEXITCODE" }

if ($SkipVaultMirror) {
  Write-Host "Skip Vault mirror (-SkipVaultMirror)." -ForegroundColor Yellow
  exit 0
}

Write-Host "==> sync_notebooklm_sources_to_mkm_data_vault.ps1" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1
if ($LASTEXITCODE -ne 0) {
  Write-Warning "Vault mirror exit $LASTEXITCODE (mount G: or set MKM_VAULT_ROOT). Lens packs are under reports/notebooklm_lens_packs_v1/"
}
