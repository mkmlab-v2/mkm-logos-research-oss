# 16-State Interface Insertion Contract (2026-03-31)

Purpose: define a runtime-ready insertion contract for 16-state normalization without forcing immediate cutover.

## 1) Current status lock

- Compression runtime is active and GO with domain-router + shard policy.
- 16-state mapping remains optional and disabled by default.
- This contract introduces integration points and gates only.

## 2) Insertion point (authoritative)

- Primary insertion point: `scripts/report_multilens_performance_eval.py` inside `evaluate_report(...)`.
- Apply mapping after `compressed`/`reconstructed` are generated and route info is known, before case row append.
- Keep it side-channel metadata first; do not block compression path.

## 3) Contract types

- Contract module: `scripts/core/state16_interface.py`
- Input type: `State16Input`
  - `case_id`, `raw_text`, `compressed_text`, `reconstructed_text`
  - `route_domain`, `route_shard_id`
  - `metadata` (free-form run context)
- Output type: `State16Output`
  - `state_id` (1..16 or null)
  - `confidence` (0..1 or null)
  - `error_code`, `error_message`
- Default adapter: `NoopState16Adapter` (returns `STATE16_NOT_ENABLED`)

## 4) Error contract

- `STATE16_NOT_ENABLED`: feature flag off (expected default)
- `STATE16_INPUT_INVALID`: bad payload shape or missing fields
- `STATE16_PROVIDER_ERROR`: downstream mapper failure/timeouts
- `STATE16_OUT_OF_RANGE`: returned `state_id` outside 1..16

Errors must not fail compression evaluation in phase-1 rollout. Record them per-case and continue.

## 5) Rollout gates

Phase A (now):
- Runtime adapter = noop
- Report row includes optional `state16` object
- Gate: zero regression on existing KPI thresholds

Phase B (shadow mode):
- Real mapper enabled for logging only
- Gate:
  - `state16_error_rate <= 1%`
  - no change to `saving_rate`, `jaccard_drop_pp`, `sensitive_integrity`

Phase C (enforced mode, approval required):
- Allow state16 to influence downstream interpretation only after 7-day stable shadow
- Gate:
  - no KPI degradation vs active baseline
  - explicit sign-off recorded in decision artifact notes

## 6) Non-goals (this cycle)

- No mandatory cutover in compression runtime.
- No threshold change (`saving>=0.50`, `jaccard_drop<=1.5`, `sensitive_integrity>=0.999`).
- No legacy-wide data migration.
