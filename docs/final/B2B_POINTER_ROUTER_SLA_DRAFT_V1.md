# B2B Hybrid Pointer Router SLA — Draft v1

Status: Draft for commercial discussion (not legal advice).

## 1) Scope

- In scope: Conditional hybrid routing for text transport/processing:
  - `GO`: pointer path eligible (with runtime guardrails)
  - `WATCH`: shadow/partial mode
  - `HOLD`: Track A fallback
- Out of scope:
  - Unconditional "99% compression" guarantee
  - Open-vocabulary perfect reconstruction guarantee
  - Legal/medical/investment outcome guarantees

## 2) Service Commitments (Fact-Safe)

- Routing safety:
  - On health alert, system auto-downgrades to `HOLD_POINTER_ROUTE` and `track_a_primary`.
  - Fallback path remains available even when pointer path is enabled.
- Availability model:
  - Runtime decision produced from policy artifacts, then transformed into runtime config.
- Evidence model:
  - Decisions, shadow reports, alerts, and guard-drill artifacts are persisted as JSON evidence.

## 3) Performance Commitment (Conditional)

Provider commits performance only when all conditions are met:

1. Client traffic/profile satisfies agreed operating zone criteria.
2. Sync policy is active: daily full + hourly delta (or stricter).
3. Guard and alert checks are healthy for the agreed lookback window.

If conditions are not met, service automatically runs Track A-safe path.

## 4) Sync and Version Control

- Full sync: once daily (off-peak).
- Delta sync: hourly.
- Emergency hotfix: on-demand patch sync.
- Version mismatch action: immediate downgrade to Track A primary.

## 5) SLI / Reporting

- Required:
  - pointer candidate-ok rate
  - unresolved token rate
  - alert status
  - guard application status
  - routing mode decision history
- Delivery:
  - Daily report + on-demand JSON artifact package.

## 6) Incident / Rollback

- Trigger examples:
  - health alert true
  - guard applied true
  - repeated unresolved spikes
- Automatic response:
  - pointer path disabled
  - Track A primary forced
- Operator override:
  - env disable switch or policy guard artifact

## 7) Commercial Notes

- Billing must be tied to measured operating zone and actual routed path.
- Savings claims must reference dated artifact evidence, not generic benchmark prose.

