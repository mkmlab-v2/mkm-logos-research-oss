param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location $WorkspaceRoot

Write-Host "==> 1/5 export fills (24h)" -ForegroundColor Cyan
py "projects/bitcoin-trading/scripts/export_binance_fills_to_cursor_trade_history_v1.py" --hours 24
if ($LASTEXITCODE -ne 0) { throw "export_binance_fills_to_cursor_trade_history_v1.py exit $LASTEXITCODE" }

Write-Host "==> 2/5 sync latest 24h SSOT" -ForegroundColor Cyan
py "projects/bitcoin-trading/scripts/sync_cursor_trade_history_latest_24h.py" `
  --source-dir "projects/bitcoin-trading/exports/cursor_trade_history" `
  --dest-dir "projects/bitcoin-trading/exports/cursor_trade_history"
if ($LASTEXITCODE -ne 0) { throw "sync_cursor_trade_history_latest_24h.py exit $LASTEXITCODE" }

Write-Host "==> 3/5 protective coverage check (mainnet)" -ForegroundColor Cyan
py "projects/bitcoin-trading/scripts/check_binance_usdm_protective_coverage_v1.py" --mainnet
if ($LASTEXITCODE -ne 0) { throw "check_binance_usdm_protective_coverage_v1.py exit $LASTEXITCODE" }

Write-Host "==> 4/5 trading GO/NO_GO refresh" -ForegroundColor Cyan
# NO_GO is a normal disk verdict; do not fail the whole observation loop (scheduled task LastTaskResult).
py "scripts/build_trading_go_nogo_status_v1.py" --out "docs/final/artifacts/trading_go_no_go_latest.json" --exit-zero-on-no-go
if ($LASTEXITCODE -ne 0) { throw "build_trading_go_nogo_status_v1.py exit $LASTEXITCODE" }

Write-Host "==> 5/5 strategy promotion gate refresh" -ForegroundColor Cyan
py "projects/bitcoin-trading/scripts/evaluate_trade_strategy_promotion_gate_v1.py" `
  --control-file "projects/bitcoin-trading/exports/cursor_trade_history/trades_control.json" `
  --treatment-file "projects/bitcoin-trading/exports/cursor_trade_history/trades_treatment.json" `
  --shadow-file "projects/bitcoin-trading/exports/cursor_trade_history/trades_treatment_v2_shadow.json" `
  --output-file "projects/bitcoin-trading/exports/cursor_trade_history/strategy_promotion_gate_latest.json"
if ($LASTEXITCODE -ne 0) { throw "evaluate_trade_strategy_promotion_gate_v1.py exit $LASTEXITCODE" }

Write-Host "==> 6/6 observation brief refresh" -ForegroundColor Cyan
py "scripts/build_trading_observation_brief_v1.py" --out "docs/final/artifacts/trading_observation_brief_latest.json"
if ($LASTEXITCODE -ne 0) { throw "build_trading_observation_brief_v1.py exit $LASTEXITCODE" }

Write-Host "==> 7/7 transition alert check" -ForegroundColor Cyan
py "scripts/alert_trading_observation_transitions_v1.py" `
  --brief "docs/final/artifacts/trading_observation_brief_latest.json" `
  --state "docs/final/artifacts/trading_observation_alert_state_latest.json" `
  --log "docs/final/artifacts/trading_observation_alert_log.jsonl"
if ($LASTEXITCODE -ne 0) { throw "alert_trading_observation_transitions_v1.py exit $LASTEXITCODE" }

Write-Host "[ok] trading observation loop complete" -ForegroundColor Green
