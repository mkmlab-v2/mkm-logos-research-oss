# Ops Autorun Bridge (2026-04-02)

## Current Fact-Lock Snapshot

- A-track gate: `HOLD`
- Recommended stage: `S1_SHADOW`
- VPS 24h daemon/showroom readiness: `GO`
- Weekly fused SOP (phase1 weekly_lite): success

## Key Metrics

- Chronos holdout direction match rate: `41.6667%`
- Trinity scoring:
  - `d5 hit_rate=1.0`
  - `d10 hit_rate=0.8`

## Source Artifacts

- `docs/final/artifacts/a_track_go_nogo_status_latest.json`
- `docs/final/artifacts/vps_24h_daemon_showroom_readiness_latest.json`
- `docs/final/artifacts/trinity_scoring_distribution_latest.json`

## Operational Note

NotebookLM 업로드 안정성을 위해 JSON/PY 직접 업로드 대신 MD 브리지 파일을 사용한다.
