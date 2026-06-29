# Start BigSet with Azure OpenAI profile (MKM_LLM_PRIORITY=azure_first).
# Usage: powershell -File scripts\Invoke-BigSetAzureStart_v1.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

py scripts/apply_bigset_free_tier_profile_v1.py --mode azure
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Azure key cannot pass BigSet /local-setup verify (Azure has no /key). Inject OS keychain directly.
py scripts/configure_bigset_azure_keychain_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$art = Join-Path $Root 'docs\final\artifacts\bigset_free_tier_profile_v1_latest.json'
if (-not (Test-Path -LiteralPath $art)) { throw "missing artifact: $art" }
$doc = Get-Content -LiteralPath $art -Raw -Encoding UTF8 | ConvertFrom-Json
$applied = $doc.applied
$env:SCHEMA_INFERENCE_MODEL = [string]$applied.SCHEMA_INFERENCE_MODEL
$env:POPULATE_ORCHESTRATOR_MODEL = [string]$applied.POPULATE_ORCHESTRATOR_MODEL
$env:INVESTIGATE_SUBAGENT_MODEL = [string]$applied.INVESTIGATE_SUBAGENT_MODEL
if ($applied.OPENROUTER_BASE_URL) { $env:OPENROUTER_BASE_URL = [string]$applied.OPENROUTER_BASE_URL }
# Inject OPENROUTER_API_KEY from Azure via Python (.env/DPAPI-safe parse).
$env:OPENROUTER_API_KEY = (& py -c "from scripts.bigset_free_tier_profile_v1 import load_dotenv_quiet, resolve_profile, apply_profile_to_environ; import os; load_dotenv_quiet(); apply_profile_to_environ(resolve_profile(mode='azure_openai')); print(os.environ.get('OPENROUTER_API_KEY',''))").Trim()
if (-not $env:OPENROUTER_API_KEY) { throw 'OPENROUTER_API_KEY empty after Azure profile apply — check AZURE_OPENAI_API_KEY in .env' }
$env:AZURE_OPENAI_API_KEY = $env:OPENROUTER_API_KEY

Write-Host "BigSet Azure profile: $($doc.applied.profile_mode)" -ForegroundColor Cyan
Write-Host "  SCHEMA_INFERENCE_MODEL=$($env:SCHEMA_INFERENCE_MODEL)"
Write-Host "  OPENROUTER_BASE_URL=$($env:OPENROUTER_BASE_URL)"
bigset start
