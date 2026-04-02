# Ops Autorun Loop Report (2026-04-02 22:16)

## Executed

1. `projects/bitcoin-trading/ops/windows-rehearsal/run_waiting_queue_btc_binance_daily.ps1` — success
2. `projects/bitcoin-trading/ops/windows-rehearsal/run_fused_quant_pixel_sop.ps1 -Phase1Mode weekly_lite` — success
3. `scripts/run_waiting_queue_monthly_check.ps1` — success

## Governance / Readiness

- A-track gate: `HOLD`
- Recommended stage: `S1_SHADOW`
- VPS showroom readiness: `GO`

## Latest Signals

- Trinity distribution metric now points to `KOSPI_D1_RETURN_PCT` snapshot:
  - `d5 pending_close_rate=1.0`
  - `d10 pending_close_rate=1.0`
  - latest decision: `PENDING_CLOSE`
- Insight effectiveness:
  - `is_promotion_ready=false`
  - `promotion_status=KEEP_OBSERVATION_ONLY`
  - pending_close_rate constraint currently unmet

## Fact Paths

- `docs/final/artifacts/a_track_go_nogo_status_latest.json`
- `docs/final/artifacts/vps_24h_daemon_showroom_readiness_latest.json`
- `docs/final/artifacts/trinity_scoring_distribution_latest.json`
- `docs/final/artifacts/insight_effectiveness_scoreboard_latest.json`

## Note

Current loop confirms operational continuity and conservative lock behavior; no live-stage unlock condition is met.
