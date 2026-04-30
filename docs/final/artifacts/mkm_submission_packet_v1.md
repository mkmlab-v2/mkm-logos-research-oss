# MKM Submission Packet (Draft v1)

## Abstract (KDD-style, ~180 words)

We present a two-track safety-gated inference architecture for risk-control operations over meaning-rich cross-reference signals. The system separates a K-track knowledge layer from a T-track survivorship and rollback layer, preventing direct promotion of expressive but potentially overfit signals into operational actions. Evaluation is artifact-anchored and reproducible: benchmark deltas, raw out-of-sample readiness checks, bootstrap/permutation significance, and falsification boundary scans are reported as as-of snapshots. In current evidence artifacts, the submission bundle is marked ready for publication claim under defined test conditions, with positive delta support in significance testing and a passing falsification suite. We further report explicit failure boundaries (first non-pass thresholds) to make reviewer stress-testing feasible. Operationally, the architecture is deployed as a risk-governance control plane (Macro Risk Warning API), while exploratory corpus-bridge capabilities (Logos Resonance Explorer API, including Aramaic-inclusive pipelines) remain isolated in a research lane unless promoted by explicit gates. This design prioritizes risk-off governance, auditability, and reproducibility over directional market claims. We position the work as a safety-first engineering pattern for converting high-complexity unstructured corpora into bounded, reviewable decision support signals.

## Abstract (AAAI-style, ~150 words)

This paper introduces a two-track safety-gated inference framework for robust risk-control decision support. The approach isolates a knowledge-generation lane (K-track) from an operational survivorship lane (T-track), reducing overfitting risk when handling meaning-rich cross-reference signals. Claims are anchored to reproducible artifacts and evaluated through benchmark comparisons, raw OOS readiness, bootstrap/permutation significance, and falsification boundary checks. Under current as-of artifacts, the evidence bundle is complete, significance supports positive delta under tested conditions, and falsification checks pass with explicit first-break thresholds disclosed. The architecture is productized as two separate API surfaces: a Macro Risk Warning API for operational governance and a Logos Resonance Explorer API for research-grade corpus bridging (including Aramaic-inclusive pipelines). Crucially, research-lane outputs do not auto-promote into operational execution without explicit promotion gates. The system is designed for risk-off governance and auditability, not guaranteed directional return claims.

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

