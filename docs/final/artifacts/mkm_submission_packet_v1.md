# MKM Submission Packet (Draft v1)

## Abstract (KDD final, ~180 words)

We present a two-track safety-gated inference architecture for risk-control operations over meaning-rich cross-reference signals. The framework separates K-track (knowledge/research lane) from T-track (operational survivorship and rollback lane), preventing direct promotion of expressive but potentially overfit signals into operations. Evaluation is artifact-anchored and reproducible: multi-baseline comparison, raw out-of-sample readiness checks, bootstrap/permutation significance testing, and falsification boundary scans are all reported as as-of snapshots. Current evidence artifacts indicate bundle/readiness gates satisfied under tested conditions, significance supporting positive delta, and falsification checks with explicit first non-pass disclosure. We surface failure boundaries (max-safe and first-break thresholds) so reviewer stress-testing can target degradation points, not only pass cases. Operationally, the architecture maps to a Macro Risk Warning API for governance and risk-off control, while corpus-bridge exploration (including Aramaic-inclusive pipelines) remains in a separate research lane unless explicit promotion gates are met. The contribution is a safety-first, reproducibility-first pattern for bounded decision-support under high-complexity unstructured inputs.

## Abstract (AAAI final, ~150 words)

This paper introduces a two-track safety-gated inference framework for risk-control decision support. K-track knowledge generation is isolated from T-track operational gating, reducing promotion risk from expressive but unstable narrative signals. Claims are evaluated through reproducible artifacts: baseline comparison, raw OOS readiness, bootstrap/permutation significance, and falsification boundary checks. In current as-of artifacts, bundle/readiness gates are satisfied under tested conditions, significance supports positive delta, and first-break thresholds are explicitly disclosed. The architecture is exposed through two API surfaces: Macro Risk Warning API for operational governance and Logos Resonance Explorer API for research-grade corpus bridging, including Aramaic-inclusive pipelines. Research outputs do not auto-promote into operational triggers without explicit gate passage. The system is positioned for risk-off governance and auditability, not guaranteed directional return.

## Methods (1-page draft)

### 1. Two-track architecture

- **K-track (knowledge/research lane):** Generates meaning-rich candidate signals and corpus-bridge artifacts.
- **T-track (operational lane):** Applies survivorship filters, rollback contracts, and control-plane gates.
- **Boundary invariant:** K-track outputs are non-binding until explicit gate promotion is satisfied.

### 2. Evidence and reproducibility contract

All reported values are tied to concrete artifact paths and timestamps. The submission package uses fixed as-of artifacts for:

- benchmark comparison
- raw OOS readiness
- statistical significance
- falsification suite and boundary
- public-safe disclosure checks

### 3. Evaluation protocol

1. **Baseline comparison:** Compare proposed signal against multiple baselines (including ablation).
2. **OOS readiness:** Verify sample sufficiency and baseline coverage.
3. **Statistical test:** Bootstrap CI plus sign-flip permutation test under fixed iteration budgets.
4. **Falsification suite:** Run contract validity, survivor floor, score/defense positivity, and counterfactual gap checks.
5. **Boundary scan:** Report first non-pass threshold row for reviewer stress tests.

### 4. Product-layer mapping

- **Macro Risk Warning API (A-track-facing):** Control-plane, hold-biased risk governance.
- **Logos Resonance Explorer API (B-track-facing):** Structured corpus transformation and exploration.
- **No auto-merge rule:** Research artifacts cannot become operational triggers without promotion gates.

### 5. Runtime transparency

- Current compression-router runtime is documented as 8 active shards.
- "12AI" is treated as an architectural expansion roadmap label, not a claim of fully active 12-shard production runtime.

## Evidence Promotion Matrix (Draft)

| ID | Artifact | Current Status | Evidence Tier (Target) | Why It Matters | Promotion Conditions (Must Pass) | Manuscript Placement |
|---|---|---|---|---|---|---|
| P1 | `two_track_raw_oos_readiness_latest.json` | `research_only`, `promotion_required` | Tier A candidate | OOS sample sufficiency and baseline coverage for operational credibility | Fixed input window/params, reproducible command, as-of snapshot declaration | Main (Methods/Results) |
| P2 | `two_track_statistical_significance_report_latest.json` | `research_only`, `promotion_required` | Tier A candidate | Statistical support via p-value, CI, bootstrap/permutation | Reproducible seed/iteration setup, stable effect-size/CI recomputation | Main (Results) |
| P3 | `two_track_benchmark_comparison_latest.json` | `research_only`, `promotion_required` | Tier A candidate | Baseline-relative improvement evidence | Fixed baseline definitions, reproducible comparison chain, stable deltas | Main (Results/Table) |
| P4 | `two_track_falsification_suite_latest.json` | `research_only`, `promotion_required` | Tier A candidate | Falsification-first trust argument instead of one-sided pass claims | Re-run checks with pass criteria, rollback behavior documentation | Main (Robustness) |
| P5 | `two_track_falsification_boundary_report_latest.json` | `research_only`, `promotion_required` | Tier A candidate | First non-pass boundary disclosure for reviewer stress testing | Reproducible sensitivity grid, stable first-break threshold | Main + Appendix |

### Evidence Tier Rule

- **Tier A (Operational-Validated):** Reproducible evidence with fixed inputs, scripts, and interpretable operational linkage.
- **Tier B (Exploratory):** Useful exploratory evidence still under `research_only`; not used as final operational claim.

**Required footnote (table/figure level):**  
All values are as-of artifact snapshots under fixed evaluation settings. Tier A and Tier B evidence are intentionally separated to preserve A-track/B-track boundary integrity. No guarantee of directional market outcome is implied.

## Limitations and Compliance

### Limitations

- Current headline artifacts remain tagged `research_only` and `promotion_required`; interpretation must stay within tested scope.
- Snapshot metrics are version/run dependent and should not be treated as immutable constants.
- Exploratory corpus-bridge findings are not equivalent to production-grade execution guarantees.

### Compliance-safe disclosure

- All quantitative statements are **as-of artifact** statements.
- Outputs are for **risk-control and governance observability**, not directional investment advice.
- No guarantee of alpha, return, or market direction is implied.
- A-track operational evidence and B-track exploratory evidence must be explicitly separated in text and tables.

## Reviewer FAQ (draft)

### Q1. If artifacts are tagged `research_only`, why publish now?

The submission presents an engineering evaluation pattern and reproducibility framework under bounded conditions. We explicitly separate exploratory status from operational promotion claims.

### Q2. Are you claiming production alpha or trading advantage?

No. The system is framed as risk-off governance/control support. We do not claim guaranteed return or directional certainty.

### Q3. How do you prevent narrative leakage from research into operations?

By design: K-track and T-track are isolated. Promotion requires explicit gates; no automatic promotion is allowed.

### Q4. How can reviewers verify your claims?

Each claim maps to artifact paths and reproducible scripts, including benchmark, OOS readiness, significance, and falsification outputs.

### Q5. Why include high-complexity historical corpora at all?

They are used as stress-test corpora for context filtering and structure extraction robustness, not as doctrinal proof.

### Q6. What is your strongest safety control?

The falsification boundary disclosure (first non-pass threshold) and rollback-oriented gating in the operational lane.

