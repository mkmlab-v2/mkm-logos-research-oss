#Requires -Version 5.1
<#
.SYNOPSIS
  Ensemble v2 strict pass -> promotion artifacts, streak bump, evidence pack (B-track opt-in).

.DESCRIPTION
  1) Optional: run ensemble v2 recommended eval (--ensemble-v2-lane)
  2) Re-eval gates on recommended_chain streak until strict_pass_streak >= 5 (lightweight re-gates)
  3) Copy strict gates to docs/final/artifacts/prophecy_promotion_gates_v1_latest.json
  4) Build prophecy_gate_evidence_pack + refresh gut_brain promotion status JSON

  Does NOT enable live trading or A-track routing. Human sign-off still required for release packet.

.PARAMETER WorkspaceRoot
  Repo root (default C:\workspace).

.PARAMETER SkipEvalRun
  Skip step 1 if reports/*_recommended_chain_* already reflect ensemble v2 lane.

.PARAMETER StreakTarget
  Target consecutive strict passes on recommended_chain streak (default 5).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Run-BtrackEnsembleV2PromotionBundle_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipEvalRun,
    [int]$StreakTarget = 5
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path -LiteralPath $WorkspaceRoot
Set-Location -LiteralPath $root

$score = "reports\btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
$lensWf = "reports\prophecy_per_date_combo_walkforward_recommended_chain_v1_latest.json"
$instWf = "reports\prophecy_instrument_combo_walkforward_recommended_chain_v1_latest.json"
$gatesRec = "reports\prophecy_promotion_gates_recommended_chain_v1_latest.json"
$streakRec = "reports\prophecy_promotion_strict_streak_recommended_chain_v1.json"
$gatesArt = "docs\final\artifacts\prophecy_promotion_gates_v1_latest.json"
$gutBrain = "docs\final\artifacts\gut_brain_agent_constitution_promotion_v1_latest.json"

if (-not $SkipEvalRun) {
    Write-Host "==> dual strict profile (v2 directions + source signal; nbps=0.4)" -ForegroundColor Cyan
    & py scripts\run_btrack_lens_v2_dual_strict_promotion_chain_v1.py --skip-bundle
    if ($LASTEXITCODE -ne 0) { throw "recommended eval failed: $LASTEXITCODE" }
}

function Get-Streak {
    if (-not (Test-Path -LiteralPath $streakRec)) { return 0 }
    $doc = Get-Content -LiteralPath $streakRec -Raw | ConvertFrom-Json
    $runs = @($doc.runs)
    $n = 0
    for ($i = $runs.Count - 1; $i -ge 0; $i--) {
        if ($runs[$i].strict_passed -eq $true) { $n++ } else { break }
    }
    return $n
}

$streak = Get-Streak
Write-Host "strict_pass_streak (before bump) = $streak / $StreakTarget" -ForegroundColor Yellow

while ($streak -lt $StreakTarget) {
    Write-Host "==> eval_prophecy_promotion_gates_v1 (streak bump $($streak + 1)/$StreakTarget)" -ForegroundColor Cyan
    & py scripts\eval_prophecy_promotion_gates_v1.py `
        --lens-walkforward-json $lensWf `
        --instrument-walkforward-json $instWf `
        --score-json $score `
        --promotion-track-mode dual `
        --strict-streak-required $StreakTarget `
        --streak-history-json $streakRec `
        --output $gatesRec
    if ($LASTEXITCODE -ne 0) { throw "gates eval failed: $LASTEXITCODE" }
    $streak = Get-Streak
}

$gateDoc = Get-Content -LiteralPath $gatesRec -Raw | ConvertFrom-Json
Write-Host "combined_all_passed=$($gateDoc.combined_all_passed) strict_passed=$($gateDoc.strict_passed) auto_promote_ready=$($gateDoc.auto_promote_ready) outcome=$($gateDoc.outcome_class)" -ForegroundColor Green

Write-Host "==> copy gates -> artifacts SSOT" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $gatesArt) | Out-Null
Copy-Item -LiteralPath $gatesRec -Destination $gatesArt -Force

Write-Host "==> evidence pack" -ForegroundColor Cyan
& py scripts\build_prophecy_gate_evidence_pack_v1.py
if ($LASTEXITCODE -ne 0) { throw "evidence pack failed: $LASTEXITCODE" }

Write-Host "==> gut_brain promotion status refresh" -ForegroundColor Cyan
& py scripts\refresh_gut_brain_btrack_promotion_status_v1.py --gates-json $gatesRec
if ($LASTEXITCODE -ne 0) { throw "gut_brain refresh failed: $LASTEXITCODE" }

Write-Host "DONE promotion bundle (B-track numeric pass_candidate; human gate for A-track/live remains)" -ForegroundColor Green
exit 0
