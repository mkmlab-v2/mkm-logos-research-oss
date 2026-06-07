<#
.SYNOPSIS
  Exa macro news fetch → news_observation staging → news/macro lens adapters (B-track).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-BtrackExaMacroNewsChain_v1.ps1
#>
param(
  [int]$NumResults = 8,
  [switch]$AppendStaging,
  [switch]$SkipFetch,
  [switch]$SkipAdapter
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $root

$dotenv = Join-Path $root 'scripts\Import-WorkspaceDotEnv_v1.ps1'
if (Test-Path -LiteralPath $dotenv) { . $dotenv -WorkspaceRoot $root }

$staging = Join-Path $root 'reports\exa_macro_news_observation_staging_v1_latest.jsonl'
$fetch = Join-Path $root 'scripts\fetch_exa_macro_news_observation_v1.py'
$adapter = Join-Path $root 'scripts\build_btrack_news_macro_lens_adapters_v1.py'

if (-not $SkipFetch) {
  if ([string]::IsNullOrWhiteSpace($env:EXA_API_KEY)) {
    Write-Host 'WARN: EXA_API_KEY missing; skip fetch (reuse staging if present).' -ForegroundColor Yellow
  } else {
    Write-Host '==> fetch_exa_macro_news_observation_v1.py' -ForegroundColor Cyan
    $fetchArgs = @($fetch, '--num-results', "$NumResults", '--validate')
    if ($AppendStaging) { $fetchArgs += '--append' }
    py @fetchArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  }
}

if (-not $SkipAdapter) {
  if (-not (Test-Path -LiteralPath $staging)) {
    Write-Host "WARN: missing staging $staging; adapter may run without Exa texts." -ForegroundColor Yellow
  }
  Write-Host '==> build_btrack_news_macro_lens_adapters_v1.py (with Exa JSONL default)' -ForegroundColor Cyan
  py $adapter --exa-news-jsonl $staging
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host 'OK: Exa macro news chain complete.' -ForegroundColor Green
