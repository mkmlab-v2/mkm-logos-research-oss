# Operator panel deck refresh: spicy FSM SSOT + operator FSM/observe + Stress Certified deck.
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

$spicyJsonl = Join-Path $WorkspaceRoot "data/wtt/examples/wtt_spicy_masked_sessions_v1.example.jsonl"
$operatorJsonl = Join-Path $WorkspaceRoot "data/wtt/examples/wtt_operator_panel_sessions_v1.example.jsonl"
$spicyFsmOut = Join-Path $WorkspaceRoot "reports/wtt_spicy_corpus_fsm_batch_v1_latest.json"
$operatorFsmOut = Join-Path $WorkspaceRoot "reports/wtt_operator_panel_fsm_batch_v1_latest.json"

Write-Host "=== WTT Operator Panel Deck Refresh ===" -ForegroundColor Cyan
Write-Host "spicy SSOT + operator observe + Stress Certified MD | SEND HOLD" -ForegroundColor Yellow

if ($DryRun) {
    Write-Host "[DryRun] spicy fsm -> operator fsm -> policy observe -> deck build" -ForegroundColor DarkGray
    exit 0
}

Write-Host "=== 1/4: spicy 25 FSM (deck proof SSOT) ===" -ForegroundColor Cyan
& py scripts/run_wtt_spicy_corpus_fsm_batch_v1.py --jsonl $spicyJsonl --out $spicyFsmOut
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== 2/4: operator panel 30 FSM ===" -ForegroundColor Cyan
& py scripts/run_wtt_spicy_corpus_fsm_batch_v1.py --jsonl $operatorJsonl --out $operatorFsmOut
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== 3/4: operator policy observe (baseline vs v2 candidate) ===" -ForegroundColor Cyan
& py scripts/observe_wtt_operator_panel_policy_v1.py --jsonl $operatorJsonl
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== 4/4: Stress Certified deck ===" -ForegroundColor Cyan
& py scripts/check_wtt_operator_panel_gate_v1.py --strict
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py scripts/build_wtt_stress_certified_deck_v1.py --fsm $spicyFsmOut
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK deck: reports/wtt_stress_certified_deck_v1_latest.md" -ForegroundColor Green
Write-Host "OK operator FSM: reports/wtt_operator_panel_fsm_batch_v1_latest.json" -ForegroundColor Green
exit 0
