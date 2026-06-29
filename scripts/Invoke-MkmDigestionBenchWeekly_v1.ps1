<#
.SYNOPSIS
  Weekly MKM digestion engine bench: pytest + production online chains + blocked-claims artifact.

.DESCRIPTION
  1) py scripts/check_mkm_digestion_production_flags_v1.py
  2) py -m pytest tests/test_mkm_digestion_engine_v1.py -q
  3) py scripts/run_mkm_digestion_engine_chain_v1.py --production (hybrid tier0 + gemini raw)
  4) py scripts/build_mkm_digestion_blocked_public_claims_v1.py
  5) py scripts/check_digested_fact_arxiv_binding_v1.py (explicit fact arxiv registry)
  6) py scripts/check_investor_deck_digestion_firewall_v1.py (deck hero firewall)

  Track B · research_only · send_gate HOLD

.PARAMETER OfflineOnly
  Steps 1-2 only (no arXiv network).

.PARAMETER WorkspaceRoot
  Repo root (default: MKM_WORKSPACE_ROOT or parent of scripts/).
#>
param(
    [switch]$OfflineOnly,
    [string]$WorkspaceRoot = ""
)

$ErrorActionPreference = "Stop"

$resolvedRoot = if (-not [string]::IsNullOrWhiteSpace($WorkspaceRoot) -and (Test-Path -LiteralPath $WorkspaceRoot)) {
    $WorkspaceRoot.TrimEnd('\', '/')
}
elseif ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
}
else {
    (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

Set-Location -LiteralPath $resolvedRoot

Write-Host "digestion_bench_weekly: step 1/6 production flags guard"
py scripts/check_mkm_digestion_production_flags_v1.py
if ($LASTEXITCODE -ne 0) {
    throw "digestion production flags guard failed exit=$LASTEXITCODE"
}

Write-Host "digestion_bench_weekly: step 2/6 pytest digestion engine"
py -m pytest tests/test_mkm_digestion_engine_v1.py -q
if ($LASTEXITCODE -ne 0) {
    throw "pytest digestion engine failed exit=$LASTEXITCODE"
}

if ($OfflineOnly) {
    Write-Host "digestion_bench_weekly: offline-only OK"
    exit 0
}

$hybrid = "docs/research/raw/tier0_hybrid_ai_web_sweep_2026-06-20.md"
$gemini = "docs/research/raw/universal_root_lexicon_matrix_gemini_report_2026-06-21.md"

Write-Host "digestion_bench_weekly: step 3/6 online production chains"
py scripts/run_mkm_digestion_engine_chain_v1.py --input $hybrid --production --skip-citation-lock
if ($LASTEXITCODE -ne 0) {
    throw "hybrid tier0 digestion chain failed exit=$LASTEXITCODE"
}
py scripts/run_mkm_digestion_engine_chain_v1.py --input $gemini --production --skip-citation-lock
if ($LASTEXITCODE -ne 0) {
    throw "gemini raw digestion chain failed exit=$LASTEXITCODE"
}

Write-Host "digestion_bench_weekly: step 4/6 blocked public claims artifact"
py scripts/build_mkm_digestion_blocked_public_claims_v1.py
if ($LASTEXITCODE -ne 0) {
    throw "blocked claims build failed exit=$LASTEXITCODE"
}

$hybridDig = "docs/final/artifacts/tier0_hybrid_ai_web_sweep_2026-06-20_digested_facts_latest.json"
$geminiDig = "docs/final/artifacts/universal_root_lexicon_matrix_gemini_report_2026-06-21_digested_facts_latest.json"

Write-Host "digestion_bench_weekly: step 5/6 arxiv binding registry check"
py scripts/check_digested_fact_arxiv_binding_v1.py --input $hybridDig --input $geminiDig
if ($LASTEXITCODE -ne 0) {
    throw "arxiv binding check failed exit=$LASTEXITCODE"
}

Write-Host "digestion_bench_weekly: step 6/6 investor deck digestion firewall"
py scripts/check_investor_deck_digestion_firewall_v1.py
if ($LASTEXITCODE -ne 0) {
    throw "investor deck digestion firewall failed exit=$LASTEXITCODE"
}

Write-Host "digestion_bench_weekly: OK artifacts=docs/final/artifacts/mkm_digestion_blocked_public_claims_latest.json"
exit 0
