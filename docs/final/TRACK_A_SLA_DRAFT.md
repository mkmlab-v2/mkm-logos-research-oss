# Track A (Universal) Service Level — Draft

**Status:** DRAFT — internal planning only. Not legal advice, not a customer-facing warranty, not a substitute for regulated-domain review.

**Aligned with:** `docs/final/COMPRESSION_SLA_POLICY_V1.md` (Track A vs Track B), `docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md`, `docs/final/P0_COMMERCIALIZATION_TRACKER.md`.

## 1. Scope

- **In scope:** Bench-linked **universal** compression profile (strategy/intensity/caps from `MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json` or successor) as implemented in `scripts/run_ultra_compression_default.py` and exercised via `scripts/report_multilens_performance_eval.py` / stub `scripts/compression_token_api_stub.py`.
- **Out of scope:** Literal-priority Track B / ultra-literal research rows used as **compliance seals**; clinical, legal, or investment **outcome** guarantees; o200k vs internal token proxy mismatch as a billing dispute resolver.

## 2. Indicative metrics (refresh before external cite)

Reference snapshots are **artifact-bound**; re-run scripts to regenerate.

- **Token economy (Track A bench):** `global_token_saving_rate` on `MULTILENS_PERFORMANCE_EVAL_INPUT_V2` is on the order of ~0.47 in the latest stored active report — see `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json` (`compression_metrics`).
- **Reconstruction proxy:** Bench `avg_reconstruction_fidelity_jaccard` on the same input has been on the order of ~0.85 in that snapshot; literal profiles target higher Jaccard at lower saving — see `COMPRESSION_SLA_POLICY_V1.md`.

Meaning: **semantic drift** (lost paraphrase, reordering) is expected at this Jaccard band; clients must not treat output as bitwise-identical to source without separate verification.

## 3. Metering and evidence

- Optional append-only log: `POST /v1/metering/log` or `eval_context.meter_log` on `POST /v1/compress` when metrics include `token_in` / `token_out` — `scripts/core/billing_meter.py`, default path under `reports/constitution/btrack_pilot/track_a_metering_log_v1.jsonl`.
- **Shadow / distribution evidence:** `scripts/run_track_a_shadow_corpus_eval.py` and `track_a_conversational_cost_simulation_latest.json` — operational traffic requires org-specific JSONL and privacy review.

## 4. Tier routing (draft intent)

- **Tier 1 (lower risk):** General conversational segments may use Track A when gates pass.
- **Tier 2 (higher risk):** Domains requiring high reconstructive fidelity should use literal / ultra-literal caps or bypass compression — router and product policy must enforce this outside this draft.

## 5. Liability and reliance

- No party should rely on this draft as an **SLA**, **SLI**, or **indemnity** baseline until versioned, approved, and attached to a contract.
- **Jaccard ~0.73** does not enumerate permissible error types for regulated use cases; partners define acceptable loss patterns and human review.

## 6. Revision

- Bump this draft when Track A caps, artifact paths, or metering schema change; keep cross-links to `COMPRESSION_SLA_POLICY_V1.md` current.
