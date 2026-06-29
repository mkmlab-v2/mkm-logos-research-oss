# Start BigSet with free-tier LLM profile (OpenRouter :free or Ollama).
# Usage: powershell -File scripts\Invoke-BigSetFreeTierStart_v1.ps1 [-Ollama]

param(
    [switch]$Ollama
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$applyArgs = @('scripts/apply_bigset_free_tier_profile_v1.py')
if ($Ollama) { $applyArgs += '--mode', 'ollama' }
py @applyArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Re-apply to current shell from artifact (py child env does not persist).
$art = Join-Path $Root 'docs\final\artifacts\bigset_free_tier_profile_v1_latest.json'
if (-not (Test-Path -LiteralPath $art)) { throw "missing artifact: $art" }
$doc = Get-Content -LiteralPath $art -Raw -Encoding UTF8 | ConvertFrom-Json
$applied = $doc.applied
$env:SCHEMA_INFERENCE_MODEL = [string]$applied.SCHEMA_INFERENCE_MODEL
$env:POPULATE_ORCHESTRATOR_MODEL = [string]$applied.POPULATE_ORCHESTRATOR_MODEL
$env:INVESTIGATE_SUBAGENT_MODEL = [string]$applied.INVESTIGATE_SUBAGENT_MODEL
if ($applied.OPENROUTER_BASE_URL) { $env:OPENROUTER_BASE_URL = [string]$applied.OPENROUTER_BASE_URL }
if ($Ollama) { $env:OPENROUTER_API_KEY = 'ollama' }
else {
  $keyOut = py -c "import sys; sys.path.insert(0, r'$Root'); from scripts.configure_bigset_local_credentials_v1 import _load_dotenv_quiet, _resolve_secret; _load_dotenv_quiet(); k=(_resolve_secret('OPENROUTER_API_KEY') or '').strip(); sys.stdout.write(k)"
  if ($keyOut) { $env:OPENROUTER_API_KEY = [string]$keyOut }
}

Write-Host "BigSet free-tier profile: $($doc.applied.profile_mode)" -ForegroundColor Cyan
Write-Host "  SCHEMA_INFERENCE_MODEL=$($env:SCHEMA_INFERENCE_MODEL)"
Write-Host "  POPULATE_ORCHESTRATOR_MODEL=$($env:POPULATE_ORCHESTRATOR_MODEL)"
bigset start
