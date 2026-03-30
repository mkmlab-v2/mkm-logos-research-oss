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
- Implementation-ready insertion contract (no cutover): `docs/final/STATE16_INTERFACE_INSERTION_CONTRACT_2026-03-31.md`

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

### 6.1 Benchmark profile and evidence refresh (Fact-Lock)

- **Default eval input**: `docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json`; **baseline report**: `MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json`.
- **Active profile runner (light, ~seconds)**: `py scripts/run_ultra_compression_default.py` — reads `MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json`, runs `evaluate_report` with `use_domain_router=True` (4-zone pilot), rewrites `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`.
- **Full grid bench (heavy)**: `py scripts/run_ultra_compression_bench.py` — round1 sweeps strategies `A|B|C`, intensities `high|ultra|extreme`, hangul flag; round2 sweeps cap grid on pareto seeds; emits `MULTILENS_ULTRA_COMPRESSION_ROUND1_V1.json`, `ROUND2`, `DECISION`, `BASELINE_LOCK`. Not required on every commit.
- **Master codebook lexicon V1** (`export_master_codebook_v1.py`) is **not** wired into the compression router path; ultra metrics remain defined by multilens eval inputs until an explicit integration milestone.

## 7) Terminology lock (anti-confusion)

- "12AI implemented": currently means **routing orchestration policy is active with a 4-zone pilot router**.
- "12AI" does **not** imply 12 subagents must run, and does **not** imply a 1:1 binding between codebook domain count and agent count.
- "Codebook": currently means shard JSON policy + template/codebook assets, not only one file.
- "4D compression": transformation engine concept used by runtime strategy path.
- "Post-it metadata": practical hint fields retained for reconstruction/evaluation context.

## 8) Change control

- If runtime path changes, update this file first, then update:
  - `docs/NotebookLM_sources_manifest.md`
  - `scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1`
  - `docs/final/openapi_token_compression_stub_v1.yaml` (when compression API contract changes)

## 9) Master Codebook V1 (lexicon rail snapshot) — completion rubric

- **Done means**: export JSON validates schema `master_codebook_lexicon_v1`, `row_count` matches emitted entries, `inputs` lists hashed paths for `master_atoms_morphhb_seed_latest.jsonl` and `master_atoms_lexicon_seed_latest.jsonl`.
- **Symbol key**: stable `atom_id` from master atoms; MorphHB row uses `morphhb_chosen` when present else index row only.
- **Scope (V1)**: Hebrew + Greek + other langs from atom catalog with per-row `lexicon_rail` / `morphhb_match_method`; **not** the product “14K clustered symbols” target (that is milestone 1b, separate plan).
- **Filename**: use `master_codebook_lexicon_v1_{row_count}_rows_latest.json` under `reports/constitution/btrack_pilot/` (avoid fixed `14K` in the name until cardinality is SSOT).
- **Reproduce**: `py scripts/export_master_codebook_v1.py` after `map_master_atoms_morphhb_seed.py` and optional `resolve_morphhb_multi_deterministic.py --write-latest`.

### 9.1 Token API data contract (hydration SSOT)

- **Canonical spec**: `docs/final/openapi_token_compression_stub_v1.yaml` — `api_contract_version` (HTTP shape semver), optional `eval_context` (paths/hints aligned with §6.1 inputs such as `MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json`), optional `hydration_hints.atom_ids` for future symbol↔row join (Master Codebook V1 `atom_id`; **no 4D vectors in this contract**).
- **Stub**: `scripts/compression_token_api_stub.py`; `compression_metrics` can be populated by live eval (`metrics_mode=live`) or decision fallback (`metrics_mode=decision_fallback`).
- **Version bump rule**: PATCH=docs/examples only, MINOR=additive backward-compatible fields, MAJOR=required field change/removal or behavior-breaking contract change.
- **Hydration mix monitor**: `py scripts/report_token_api_hydration_mix.py` → `reports/constitution/btrack_pilot/token_api_hydration_mix_latest.json` (tracks `metrics_mode` counts and `live_ratio`).
- **KPI summary snapshot**: `py scripts/report_ultra_compression_kpi_summary.py` → `reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json` (decision/quality/perf/hydration in one JSON).
- **3-mode demo runner (PowerShell)**: `pwsh -File scripts/demo_token_api_modes.ps1` (none/decision_fallback/live + expand roundtrip).

Status: Fact-Lock active (2026-03-31).
