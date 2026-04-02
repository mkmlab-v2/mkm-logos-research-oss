# Ops Notebook-Driven Loop (2026-04-02 23:46)

## Auto Execution Rule

NotebookLM 지휘부 우선순위 3개를 그대로 자동 실행.

## Executed

1. `projects/bitcoin-trading/ops/windows-rehearsal/run_waiting_queue_btc_binance_daily.ps1` — success
2. `projects/bitcoin-trading/ops/windows-rehearsal/run_fused_quant_pixel_sop.ps1 -Phase1Mode weekly_lite` — success
3. `scripts/run_waiting_queue_monthly_check.ps1` — success
4. BTC metric lock refresh:
   - `scripts/report_trinity_scoring_distribution.py --metric BTC_BINANCE_D1_RETURN_PCT --output docs/final/artifacts/trinity_scoring_distribution_btc_latest.json`

## BTC Snapshot

- d5/d10 hit_rate: `1.0 / 1.0`
- latest_decision: `HIT`
- dual_regime advisory: `state_clamp_stable`
- total_filtered_rows: `44`

## Additional Runtime Note

이번 사이클 브로드캐스트에서 `net_source_fallback_active`가 1회 관측됨(금지 조건은 아님, 추세 모니터링 권장).
