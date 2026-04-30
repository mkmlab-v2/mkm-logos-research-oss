# MKM Submission Table/Figure Caption Templates (v1)

## Caption Rules

- Always include: as-of date/time, artifact path, lane label (A-track or B-track).
- Use bounded wording: "under tested conditions", "in this snapshot", "in this run."
- Avoid absolute language: "proves", "guarantees", "always."

## Table Caption Templates

### Table 1: Benchmark Comparison

**Template:**  
Table 1. Baseline vs proposed shift-score comparison under fixed evaluation settings (as-of `<timestamp>`; artifact: `<path>`). Results indicate relative improvement under tested conditions; no directional return guarantee is implied.

### Table 2: OOS Readiness

**Template:**  
Table 2. Out-of-sample readiness summary with sample sufficiency and baseline coverage checks (as-of `<timestamp>`; artifact: `<path>`). This table reports readiness status for reproducibility and review, not trading advice.

### Table 3: Statistical Significance

**Template:**  
Table 3. Bootstrap/permutation significance results for benchmark deltas (as-of `<timestamp>`; artifact: `<path>`). P-values and confidence intervals reflect the specified test setup and run conditions.

### Table 4: Falsification and Boundary

**Template:**  
Table 4. Falsification suite pass/fail and first non-pass boundary row (as-of `<timestamp>`; artifacts: `<path1>`, `<path2>`). Boundary disclosure is included to expose failure conditions, not only pass outcomes.

## Figure Caption Templates

### Figure 1: Two-Track Architecture

**Template:**  
Figure 1. Two-track architecture separating K-track (knowledge generation) and T-track (operational survivorship/rollback). K-track outputs do not auto-promote to operational triggers without explicit gate passage.

### Figure 2: Evaluation Pipeline

**Template:**  
Figure 2. Reproducibility pipeline from benchmark and OOS checks to significance and falsification boundary reporting. Each stage maps to versioned artifacts and scripts.

### Figure 3: Failure Boundary Visualization

**Template:**  
Figure 3. Falsification sensitivity grid highlighting first non-pass threshold (as-of `<timestamp>`; artifact: `<path>`). The boundary marks where validation begins to degrade under tested constraints.

### Figure 4: Product Surface Separation

**Template:**  
Figure 4. Product-layer split between Macro Risk Warning API (A-track operational governance) and Logos Resonance Explorer API (B-track exploratory analysis), with explicit no-auto-merge policy.

## Example Placeholder Block (Copy/Paste)

- as-of: `<YYYY-MM-DDTHH:MM:SSZ>`
- artifact: `<docs/final/artifacts/..._latest.json>`
- lane: `<A-track|B-track>`
- claim scope: `<tested conditions only>`

