# W4 Approval Packet Index V1

## Purpose
- Single entrypoint for reviewing B-track W3-W4 promotion readiness.

## Review Order
1. Decision summary: `docs/final/artifacts/W4_PROMOTION_DECISION_FINAL.md`
2. Batch stability summary: `docs/final/artifacts/W3_MULTI_BATCH_STABILITY_SUMMARY_V1.json`
3. Threshold sensitivity: `docs/final/artifacts/W3_GATE_THRESHOLD_SWEEP_V1.json`
4. Current batch result: `docs/final/artifacts/W3_RESONANCE_BATCH_RESULT_V1.json`
5. Compute contract: `docs/final/artifacts/W3_RESONANCE_COMPUTE_SPEC_V1.json`
6. Gate readiness baseline: `docs/final/artifacts/W2_GATE_READINESS_NOTE.json`

## Required Checks
- Promotion gate is passed on required runs.
- False-equivalence and deterministic-wording risk counts are within threshold.
- Notice integrity checks pass for personal lane.
- B-track isolation is preserved; no A-track merge is included.

## Approval Checklist
- [ ] Confirm gate metrics and threshold policy are acceptable.
- [ ] Confirm residual risks are documented and acceptable.
- [ ] Confirm A-track promotion remains approval-gated.
- [ ] Approve controlled next expansion scope (if any).

## Notes
- This packet does not authorize A-track merge or trading-trigger integration by itself.
