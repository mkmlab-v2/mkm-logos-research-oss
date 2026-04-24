# 12AI Orchestration Gate - Issue Response v1

## Scope

This runbook maps orchestration gate `issue_code` values to immediate operator actions.

## Issue Codes and Actions

- `RETRY_STRATEGY_REQUIRED`
  - Meaning: retry count reached gate threshold (`retries >= 3`) without `action=change_strategy`.
  - Action: switch to `change_strategy` and re-run with one of: scope reduction, alternate implementation, or evidence refresh.

- `PROMOTION_LATENCY_GATE_FAILED`
  - Meaning: `latency_improvement < 15`.
  - Action: verify baseline/current artifact pairing first, then optimize hot path or hold promotion.

- `PROMOTION_ERROR_RATE_GATE_FAILED`
  - Meaning: `error_rate_reduction < 20`.
  - Action: inspect failing requests/errors, stabilize regression, and re-run metric chain before promotion.

- `MUTATOR_BRANCH_ISOLATION`
  - Meaning: `Role=Mutator` attempted outside `b-track-*` branch naming.
  - Action: move changes to `b-track-*` branch and re-run checks.

- `BASELINE_LOCK_MISSING_HASH`
  - Meaning: lock file does not contain baseline hash.
  - Action: update lock through `scripts/update_12ai_baseline_lock.ps1 -ConfirmUpdate` after human review.

- `BASELINE_LOCK_PATH_MISMATCH`
  - Meaning: lock file baseline path does not resolve to runtime baseline path.
  - Action: reconcile path in lock file with runtime config and re-verify lock.

- `BASELINE_LOCK_HASH_MISMATCH`
  - Meaning: baseline artifact hash drifted from lock.
  - Action: block promotion, validate baseline refresh intent, then update lock with explicit approval switch.

## Baseline Refresh Procedure

1. Human review baseline artifact validity.
2. Run:
   - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/update_12ai_baseline_lock.ps1 -BaselineMetricsPath docs/final/artifacts/bench_l1_api_load_summary_vps_latest.json -LockFilePath docs/final/artifacts/orchestration_gate_baseline_lock_v1.json -ApprovedBy <reviewer> -ConfirmUpdate`
3. Verify:
   - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_12ai_baseline_lock.ps1`
