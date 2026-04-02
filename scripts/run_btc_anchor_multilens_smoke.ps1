# BTC B-track anchor (3 calendar days): market adapter (Binance+FGI) + Thin V2 harness + Sasang JSONL.
# SSOT dates: data/multilens_eval/curated_dates_btc_anchor_smoke_v1.json
# Sasang lines: data/sasang/sasang_dynamics_regime_mapping_v1.btc_anchor_smoke.jsonl
# Requires network for adapter. See CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md §3.6.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\run_btc_anchor_multilens_smoke.ps1

param()

$ErrorActionPreference = "Stop"
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $workspaceRoot

$curated = Join-Path $workspaceRoot "data\multilens_eval\curated_dates_btc_anchor_smoke_v1.json"
$adapterOut = Join-Path $workspaceRoot "data\multilens_eval\dual_regime_market_adapter_btc_anchor_smoke_v1.json"
$sasang = Join-Path $workspaceRoot "data\sasang\sasang_dynamics_regime_mapping_v1.btc_anchor_smoke.jsonl"
$reportOut = Join-Path $workspaceRoot "data\multilens_eval\multilens_eval_v2_thin_report_btc_anchor_smoke_v1.json"

Write-Host "== multilens_dual_regime_market_adapter_v1 (BTC anchor dates) ==" -ForegroundColor Cyan
& py (Join-Path $workspaceRoot "scripts\multilens_dual_regime_market_adapter_v1.py") @(
    "--curated", $curated,
    "--out", $adapterOut
)
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== eval_multilens_harness_v2_thin (populate + Sasang + adapter) ==" -ForegroundColor Cyan
& py (Join-Path $workspaceRoot "scripts\eval_multilens_harness_v2_thin.py") @(
    "--curated", $curated,
    "--populate-default-samples",
    "--sasang-jsonl", $sasang,
    "--dual-regime-json", $adapterOut,
    "--out", $reportOut
)
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK: $reportOut" -ForegroundColor Green
exit 0
