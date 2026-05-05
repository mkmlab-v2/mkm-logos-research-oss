# ATHENA Fact-Lock Snapshot V1

Purpose: Provide Gemini/NotebookLM with current local JSON truth values.
Rule: When values conflict with older NotebookLM context, this snapshot wins.

Generated At (UTC): <YYYY-MM-DDTHH:MM:SSZ>
Snapshot Version: v1

## Source Files
- `docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.json`
- `docs/final/artifacts/integrated_governance_v1_latest.json`
- `docs/final/artifacts/a_track_go_nogo_status_latest.json`

## Canonical path/key/value

### 1) prophecy_2026_monthly_kospi_btc_fact_safe_v1.json
- path: `docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.json`
- key/value: `meta.high_reliability_decision` / `<HOLD|WATCH|...>`
- key/value: `meta.price_output_locked` / `<true|false>`
- key/value: `risk_profile.mode` / `<LOCKED_MODE|...>`

### 2) integrated_governance_v1_latest.json
- path: `docs/final/artifacts/integrated_governance_v1_latest.json`
- key/value: `final_regime` / `<ATTACK|...>`
- key/value: `final_score` / `<number>`
- key/value: `final_action_allowed` / `<true|false>`

### 3) a_track_go_nogo_status_latest.json
- path: `docs/final/artifacts/a_track_go_nogo_status_latest.json`
- key/value: `result.overall_go_no_go` / `<HOLD|GO|...>`
- key/value: `result.recommended_stage` / `<S1_SHADOW|...>`
- key/value: `snapshot.chronos_holdout_direction_match_rate` / `<number>`
- key/value: `result.failed_reasons` / `<json array raw>`

## PASS/FAIL Contract (for Athena check)
- PASS only when all expected values match this snapshot.
- If any key missing or stale, output `확인 필요` and set conservative decision to HOLD.

## Optional Lens Readiness (if used)
- path: `docs/final/artifacts/kospi_myeongri_standalone_commercial_gate_v1_latest.json`
  - key/value: `standalone_commercial_ready` / `<true|false>`
- path: `docs/final/artifacts/kospi_sasang_single_lane_commercial_gate_v1_latest.json`
  - key/value: `commercial_ready` / `<true|false>`
- path: `docs/final/artifacts/kospi_biblical_single_lane_commercial_gate_v1_latest.json`
  - key/value: `precommercial_ready` / `<true|false>`
  - key/value: `stability.current_ready_streak` / `<number>`
  - key/value: `stability.stability_go` / `<true|false>`
