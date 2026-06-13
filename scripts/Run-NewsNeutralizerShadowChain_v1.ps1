# B-track news neutralizer shadow chain (research_only · no auto public deck).
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-NewsNeutralizerShadowChain_v1.ps1
#   ... -Live   # LLM + RSS (default billing auto → Azure when AZURE_OPENAI_* set)
#   ... -Live -Billing azure
#   ... -Fixture  # offline fixture RSS

param(
    [switch]$Live,
    [switch]$Fixture,
    [ValidateSet("auto", "azure", "developer", "vertex")]
    [string]$Billing = "auto",
    [string]$AzureDeployment = "",
    [int]$MaxCards = 5,
    [int]$MaxClusters = 5,
    [int]$AzureInterCallSleep = 20,
    [switch]$SkipPytest
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$neutralizerArgs = @('--strict-lint', '--max-clusters', $MaxClusters, '--billing', $Billing)
if ($Live) {
    $neutralizerArgs += '--live'
    if ($AzureInterCallSleep -ge 0) {
        $neutralizerArgs += @('--azure-inter-call-sleep', $AzureInterCallSleep)
    }
} else {
    $neutralizerArgs += '--dry-run'
}
if ($AzureDeployment) {
    $neutralizerArgs += @('--azure-deployment', $AzureDeployment)
}
if ($Fixture) {
    $neutralizerArgs += '--fixture'
}

Write-Host "[1/3] news neutralizer shadow..." -ForegroundColor Cyan
& py scripts/test_news_neutralizer_v1.py @neutralizerArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/3] map shadow -> deck candidates (artifacts only)..." -ForegroundColor Cyan
& py scripts/map_news_neutralizer_shadow_to_deck_candidates_v1.py --max-cards $MaxCards --strict-lint
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipPytest) {
    Write-Host "[3/3] pytest smoke..." -ForegroundColor Cyan
    & py -m pytest tests/test_news_neutralizer_v1.py tests/test_news_neutralizer_llm_v1.py tests/test_map_news_neutralizer_shadow_to_deck_candidates_v1.py -q
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "[3/3] refresh candidates from latest shadow (post-pytest)..." -ForegroundColor Cyan
    & py scripts/map_news_neutralizer_shadow_to_deck_candidates_v1.py --shadow-json reports/news_neutralizer_shadow_v1_latest.json --max-cards $MaxCards --strict-lint
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "[3/3] skip pytest (-SkipPytest)" -ForegroundColor DarkYellow
}

Write-Host "Run-NewsNeutralizerShadowChain_v1: OK (shadow + candidates; public deck untouched)" -ForegroundColor Green
exit 0
