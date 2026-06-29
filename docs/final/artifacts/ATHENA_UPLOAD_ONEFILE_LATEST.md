# ATHENA Upload Onefile (Latest)

Use this single file for Gemini/NotebookLM upload.
Do not move original artifacts. This file is a derived snapshot only.

Generated At (UTC): 2026-06-28T15:40:02Z

## Source of truth (unchanged original paths)
- `docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.json`
- `docs/final/artifacts/integrated_governance_v1_latest.json`
- `docs/final/artifacts/a_track_go_nogo_status_latest.json`
- `docs/final/artifacts/kospi_myeongri_standalone_commercial_gate_v1_latest.json`
- `docs/final/artifacts/kospi_sasang_single_lane_commercial_gate_v1_latest.json`
- `docs/final/artifacts/kospi_biblical_single_lane_commercial_gate_v1_latest.json`

## Canonical path/key/value snapshot

### 1) prophecy_2026_monthly_kospi_btc_fact_safe_v1.json
- path: `docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.json`
- key/value: `meta.high_reliability_decision` / "HOLD"
- key/value: `meta.price_output_locked` / true
- key/value: `risk_profile.mode` / "LOCKED_MODE"

### 2) integrated_governance_v1_latest.json
- path: `docs/final/artifacts/integrated_governance_v1_latest.json`
- key/value: `final_regime` / "ATTACK"
- key/value: `final_score` / 0.50023
- key/value: `final_action_allowed` / true

### 3) a_track_go_nogo_status_latest.json
- path: `docs/final/artifacts/a_track_go_nogo_status_latest.json`
- key/value: `result.overall_go_no_go` / "GO"
- key/value: `result.recommended_stage` / "S4_LIMITED_LIVE"
- key/value: `snapshot.chronos_holdout_direction_match_rate` / 50.857142857142854
- key/value: `result.failed_reasons` / []

### Lens readiness
- path: `docs/final/artifacts/kospi_myeongri_standalone_commercial_gate_v1_latest.json`
- key/value: `standalone_commercial_ready` / true
- key/value: `metrics.abs_train_test_acc_gap` / 0.001801

- path: `docs/final/artifacts/kospi_sasang_single_lane_commercial_gate_v1_latest.json`
- key/value: `commercial_ready` / true
- key/value: `latest_single_lane_gate.precommercial_ready` / true

- path: `docs/final/artifacts/kospi_biblical_single_lane_commercial_gate_v1_latest.json`
- key/value: `precommercial_ready` / true
- key/value: `stability.current_ready_streak` / 2
- key/value: `stability.stability_go` / false

## Forced decision rules for Athena
- If `meta.high_reliability_decision=="HOLD"` OR `meta.price_output_locked==true`, Final Action must be `HOLD`.
- Even if `final_regime=="ATTACK"`, apply `most_conservative_wins`.
- Final Action reason must reuse `result.failed_reasons` raw array.

## Final fixed line
"현재 증거 범위에서는 운영 가능하나, Unverified Items 해소 전까지 HOLD 가드레일을 유지합니다."
