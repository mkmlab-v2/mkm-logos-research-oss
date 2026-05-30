#Requires -Version 5.1
<#
.SYNOPSIS
  Recommended Logos candidate-edge path: refresh queue + gates + commander review pack (ANN-lite first).
  Does NOT auto-approve signoff or merge canonical edges.
.EXAMPLE
  pwsh -NoProfile -File scripts/Run-LogosCandidateEdgeHumanReviewRecommended_v1.ps1
#>
param(
  [switch]$SkipPytest,
  [switch]$RefreshAgentSearch
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "==> Logos candidate-edge human review (recommended: ann_lite primary)" -ForegroundColor Cyan

py scripts/build_logos_candidate_edge_human_review_queue_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/run_logos_candidate_edge_review_promotion_chain_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/build_logos_candidate_edge_human_review_pack_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipPytest) {
  py -m pytest tests/test_logos_candidate_edge_human_review_v1.py -q --tb=short
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($RefreshAgentSearch) {
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-AgentSearchCorpusUploadAndImport_v1.ps1 `
    -Profile logos-ops -SkipGemini `
    -Query "Logos human review pack ann_lite" `
    -Question "What is the recommended review order for candidate edges?"
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[OK] reports/logos_candidate_edge_human_review_pack_v1_latest.md" -ForegroundColor Green
Write-Host "     docs/final/artifacts/logos_candidate_edge_human_review_queue_v1_latest.json" -ForegroundColor Green
Write-Host "[NOTE] signoff approved=false — 지휘관 ANN-lite 45 검수 후 signoff JSON 갱신" -ForegroundColor Yellow
exit 0
