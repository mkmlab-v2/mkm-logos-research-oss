# 1+3 Execution Schedule v1

- generated_at_utc: `2026-05-05T16:00:00Z`
- mode: `local-first / conflict-minimized`
- scope: `7d/14d threshold tuning + warning/critical dual gate`

## Phase 0 - Lock Inputs (D0)
- Freeze policy baseline in `one_plus_three_threshold_policy_v1.json`.
- Confirm metric producer path for:
  - `window_7d_metrics`
  - `window_14d_metrics`
  - `latest_gate_state`
- Exit criteria: policy + input contract both pinned.

## Phase 1 - Gate Engine (D0-D1)
- Implement independent decision runner:
  - `scripts/run_one_plus_three_warning_critical_gate_v1.py`
- Output artifact:
  - `docs/final/artifacts/one_plus_three_gate_decision_latest.json`
- Exit criteria: script runs from CLI with deterministic level output.

## Phase 2 - Test and Guard (D1)
- Add unit tests for `ok/warning/critical` paths.
- Command:
  - `py -m pytest tests/test_run_one_plus_three_warning_critical_gate_v1.py -q`
- Exit criteria: all tests pass.

## Phase 3 - Dry Integration (D1-D2)
- Feed runner with real latest metrics artifact (no auto promotion).
- Validate expected fail-close behavior for critical path.
- Exit criteria: reason codes and actions are audit-ready.

## Phase 4 - Ops Wiring (D2)
- Add optional chain hook (feature flag / switch only).
- Keep existing production chain unchanged by default.
- Exit criteria: integration can be turned on/off safely.

## Phase 5 - Promotion Readiness (D3)
- Collect 7-day decision history.
- Review false positive/negative rate for warning and critical.
- Exit criteria: manual approval packet complete.

## DoD Checklist
- [ ] policy file locked
- [ ] decision runner implemented
- [ ] ok/warning/critical tests passed
- [ ] latest decision artifact generated
- [ ] P0 path verification passed
- [ ] manual approval checkpoint recorded
