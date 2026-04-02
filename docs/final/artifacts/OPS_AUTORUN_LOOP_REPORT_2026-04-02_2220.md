# Ops Autorun Loop Report (2026-04-02 22:20)

## Executed

1. `scripts/run_a_track_weekly_check.ps1 -OnSystemError no_go -DryRun` — success
2. `projects/bitcoin-trading/ops/windows-rehearsal/run_waiting_queue_btc_binance_daily.ps1` — success
3. `scripts/report_trinity_scoring_distribution.py --metric BTC_BINANCE_D1_RETURN_PCT --output docs/final/artifacts/trinity_scoring_distribution_btc_latest.json` — success
4. `scripts/check_vps_showroom_readiness.py` — success

## Core Status

- A-track: `HOLD`
- recommended stage: `S1_SHADOW`
- readiness: `GO`
- daemon_running_flag: `true`

## BTC Metric Lock Snapshot

- file: `docs/final/artifacts/trinity_scoring_distribution_btc_latest.json`
- d5: `hit_rate=1.0`, `pending_close_rate=0.0`
- d10: `hit_rate=1.0`, `pending_close_rate=0.0`
- latest_decision: `HIT`
- total_filtered_rows: `21`

## Governance Note

Unlock condition remains blocked by high-reliability HOLD and Chronos holdout threshold miss.
