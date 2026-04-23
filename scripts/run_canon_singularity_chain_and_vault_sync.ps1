# Run canon-only singularity chain then mirror NotebookLM sources to MKM vault.
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\run_canon_singularity_chain_and_vault_sync.ps1
#
# Optional:
#   -CanonJsonl <path>
#   -RegimeMapJson <path>
#   -SkipVaultSync

param(
    [string]$CanonJsonl = "data/logos/verse_decoded_v2.jsonl",
    [string]$RegimeMapJson = "data/regimes/regime_map_btc_ext.json",
    [switch]$SkipVaultSync
)

$ErrorActionPreference = "Stop"
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $workspaceRoot

$chain = Join-Path $workspaceRoot "scripts\core\run_canon_singularity_chain_v1.py"
if (-not (Test-Path -LiteralPath $chain)) {
    throw "Missing chain runner: $chain"
}

Write-Host "[1/2] Run canon singularity chain" -ForegroundColor Cyan
& py $chain `
    --canon-jsonl $CanonJsonl `
    --regime-map-json $RegimeMapJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($SkipVaultSync) {
    Write-Host "[2/2] Vault sync skipped by -SkipVaultSync" -ForegroundColor Yellow
    exit 0
}

$sync = Join-Path $workspaceRoot "scripts\sync_notebooklm_sources_to_mkm_data_vault.ps1"
if (-not (Test-Path -LiteralPath $sync)) {
    throw "Missing vault sync script: $sync"
}

Write-Host "[2/2] Mirror NotebookLM sources to vault" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File $sync
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "DONE: canon singularity chain + vault sync" -ForegroundColor Green
