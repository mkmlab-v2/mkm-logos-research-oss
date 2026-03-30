# Compression Interpretation Pipeline Fact-Lock (2026-03-31)

Purpose: lock one unambiguous explanation of the current compression/interpretation flow so both humans and agents avoid role confusion.

## 1) Scope and fact policy

- This document describes the runtime path currently implemented under `scripts/`.
- Do not claim "fully implemented 12AI" from design notes alone.
- Distinguish clearly:
  - **Implemented now**: 4-shard domain routing pilot + compression benchmark engine.
  - **Planned**: full 12-shard expansion and explicit 16-state interface integration in compression runtime.

## 2) Current runtime flow (implemented)

1. Input text enters evaluation/compression runtime.
2. Domain router selects shard policy (pilot 4 zones):
   - `scripts/core/domain_router.py`
   - `codebook/shards/zone_a_scm.json`
   - `codebook/shards/zone_b_timing.json`
   - `codebook/shards/zone_c_hangul.json`
   - `codebook/shards/zone_d_ssot.json`
3. Selected shard injects policy:
   - hard keep terms (always)
   - soft keep terms (conditional)
   - hangul principle toggle
4. Compression engine runs strategy/intensity (`A|B|C`, `high|ultra|extreme`):
   - `scripts/report_multilens_performance_eval.py`
5. Metadata-like hints are retained in report rows:
   - route info (`shard_id`, `domain`)
   - effective compressed and reconstructed text fields
6. Multi-lens eval computes quality gates:
   - saving rate
   - reconstruction fidelity (jaccard)
   - sensitive integrity

## 3) Layer responsibilities (authoritative mapping)

- **12AI router layer (pilot)**: classification/routing. Decides "which domain policy should apply".
- **Codebook shard layer**: policy. Defines keep/guard/hangul behavior.
- **Compression engine layer**: transformation. Produces compressed candidate.
- **Multi-lens layer**: validation. Scores result and gates rollout.

Important: multi-lens is a quality microscope, not the primary compressor.

## 4) 16-state interface status

- 16-state (`state_id 1..16`) is a separate state system used in myeongni/state analysis paths.
- In current compression runtime, direct 16-state mapping is **not yet wired** as a mandatory normalization step.
- Therefore claims like "12AI -> 16-state compression engine already integrated" are not fact-locked yet.

## 5) Legacy compatibility status

- Legacy data is not hard-broken by router introduction.
- Router has default fallback behavior (SSOT-like shard) for unmatched text.
- However, a formal end-to-end migration pipeline for all legacy assets is not yet implemented in this compression runtime.

## 6) Operational baseline (as of 2026-03-31)

- Bench runner: `scripts/run_ultra_compression_bench.py`
- Active profile runner: `scripts/run_ultra_compression_default.py`
- Latest generated artifacts:
  - `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json`
  - `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`

Use these artifacts as runtime truth, not chat memory.

## 7) Terminology lock (anti-confusion)

- "12AI implemented": currently means **4-zone pilot router is running**.
- "Codebook": currently means shard JSON policy + template/codebook assets, not only one file.
- "4D compression": transformation engine concept used by runtime strategy path.
- "Post-it metadata": practical hint fields retained for reconstruction/evaluation context.

## 8) Change control

- If runtime path changes, update this file first, then update:
  - `docs/NotebookLM_sources_manifest.md`
  - `scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1`

Status: Fact-Lock active (2026-03-31).
