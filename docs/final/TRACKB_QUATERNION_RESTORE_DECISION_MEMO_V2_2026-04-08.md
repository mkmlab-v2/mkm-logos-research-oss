# Track B Quaternion Restore Decision Memo v2 (Research Lane)

## 1) Scope

- Lane: Track B research only (`research_only=true`).
- Objective: Validate quaternion-based distill/restore behavior with explicit GO/HOLD gate.
- Guardrail: No direct merge into production compression route without separate approval and runtime/cost tests.

## 2) Inputs and Artifacts

- Bridge artifact: `docs/final/artifacts/trackb_quaternion_restore_bridge_v1.json`
- Generalization bench (v6, restore profile): `docs/final/artifacts/trackb_quaternion_generalization_v6_restore_v2_latest.json`
- Two-stage gate (v2): `docs/final/artifacts/trackb_quaternion_two_stage_gate_v2.json`
- Failure clusters: `docs/final/artifacts/trackb_quaternion_failure_clusters_v2_latest.json`

## 3) Gate Result

- Decision: `GO` (research gate only)
- Thresholds:
  - `closed_min_exact_rate >= 0.999`
  - `open_min_exact_rate >= 0.995`
  - `open_max_collision_rate <= 0.01`
- Observed:
  - Stage1 closed exact: pass
  - Stage2 open exact: pass
  - Stage2 collision: pass

## 4) Interpretation

- Current profile (`exact_restore_guarded`) passes with strong exact-sequence restoration under tested `(lengths=3,5; oov=0.0,0.1)`.
- Failure cluster report is empty in this run (`failure_example_count=0`), which is acceptable but should be revalidated on broader length/OOV ranges before any promotion discussion.
- This result does **not** authorize billing/VRAM claims and does **not** imply operational readiness.

## 5) GO/HOLD Policy (v2)

- GO (research continuation):
  - All stage thresholds pass, artifacts generated, schema valid.
- HOLD (promotion hold):
  - Any threshold miss, or concentrated failures in specific length/OOV buckets.
  - Runtime/cost/reproducibility checks absent for production context.

## 6) Recommendation

- Keep Track B quaternion restore in research lane and continue grid expansion (`length>=7`, higher OOV bins, stress variants).
- Use bridge script outputs as read-only evidence feed for governance.
- Reassess promotion only after separate production-facing checks (latency, memory, deterministic fallback behavior).

## 7) 14-Day Execution Checklist (Track B Only)

### Day 1-2: Baseline Freeze

- [ ] Freeze run manifest template for Track B (inputs, seed, OOV buckets, command fingerprint).
- [ ] Pin artifact naming convention for weekly diffs (`*_latest.json` + dated snapshot).
- [ ] Record current baseline from `trackb_quaternion_two_stage_gate_v2.json`.

### Day 3-7: Grid Expansion

- [ ] Expand length buckets to include `length>=7`.
- [ ] Expand OOV bins beyond current default and include stress tiers.
- [ ] Generate failure cluster diff bundle and compare against prior baseline.
- [ ] Confirm schema validity and reproducibility (same seed, same command, same output shape).

### Day 8-14: Promotion Readiness Precheck

- [ ] Run latency/memory precheck in research lane (no production merge).
- [ ] Verify deterministic fallback behavior under threshold misses.
- [ ] Produce GO/HOLD summary with explicit out-of-scope statement.
- [ ] Keep status as research-only unless all gates pass with evidence.

## 8) Reporting Rule (Non-Negotiable)

- [ ] Every report starts with: measured item, artifact path, out-of-scope.
- [ ] No artifact path → no claim.
