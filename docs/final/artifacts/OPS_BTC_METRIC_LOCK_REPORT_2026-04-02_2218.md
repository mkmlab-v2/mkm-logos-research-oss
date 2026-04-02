# Ops BTC Metric Lock Report (2026-04-02 22:18)

## Purpose

KOSPI/BTC 지표 혼선을 제거하기 위해 BTC 전용 Trinity 분포 스냅샷을 별도 파일로 고정 생성.

## Generated Artifact

- `docs/final/artifacts/trinity_scoring_distribution_btc_latest.json`

## BTC Snapshot (from artifact)

- `metric`: `BTC_BINANCE_D1_RETURN_PCT`
- `d5`: `hit_rate=1.0`, `pending_close_rate=0.0`
- `d10`: `hit_rate=1.0`, `pending_close_rate=0.0`
- `latest_decision`: `HIT`
- `total_filtered_rows`: `20`

## Governance Context (unchanged)

- A-track Go/No-Go: `HOLD`
- Recommended stage: `S1_SHADOW`
- Unlock remains blocked by high-reliability HOLD + price lock + chronos holdout threshold miss.
