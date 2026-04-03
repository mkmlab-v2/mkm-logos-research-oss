# Compression Interpretation Pipeline Fact-Lock (2026-03-31)

Purpose: lock one unambiguous explanation of the current compression/interpretation flow so both humans and agents avoid role confusion.

## 1) Scope and fact policy

- This document describes the runtime path currently implemented under `scripts/`.
- Do not claim "fully implemented 12AI" from design notes alone.
- Distinguish clearly:
  - **Implemented now**: domain router loads **every** `codebook/shards/zone_*.json` file (currently **8** shards: `zone_a_scm` through `zone_h_legacy`; the original pilot was the **a–d** subset) + compression benchmark engine.
  - **Planned**: further expansion toward **12** domain shards (optional target count; not tied to agent count) and explicit 16-state interface integration in compression runtime.

## 2) Current runtime flow (implemented)

1. Input text enters evaluation/compression runtime.
2. Domain router selects shard policy by scoring `routing_keywords` across **all** loaded shards (`DomainSpecificRouter` glob: `codebook/shards/zone_*.json`):
   - `scripts/core/domain_router.py`
   - `zone_a_scm.json`, `zone_b_timing.json`, `zone_c_hangul.json`, `zone_d_ssot.json` (pilot core)
   - `zone_e_finance.json`, `zone_f_code.json`, `zone_g_health.json`, `zone_h_legacy.json` (extended zones; same loader)
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
  - **Two-track (literal profile, optional):** `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_LITERAL_V1.json` — `py scripts/run_ultra_compression_default.py --mode literal`. Policy SSOT: `docs/final/COMPRESSION_SLA_POLICY_V1.md`.

Use these artifacts as runtime truth, not chat memory.

### 6.1 Benchmark profile and evidence refresh (Fact-Lock)

- **Default eval input**: `docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json`; **baseline report**: `MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json`.
- **Active profile runner (light, ~seconds)**: `py scripts/run_ultra_compression_default.py` — reads `MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json`, runs `evaluate_report` with `use_domain_router=True` (all `zone_*.json` shards under `codebook/shards/`), rewrites `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`.
- **Full grid bench (heavy)**: `py scripts/run_ultra_compression_bench.py` — round1 sweeps strategies `A|B|C`, intensities `high|ultra|extreme`, hangul flag; round2 sweeps cap grid on pareto seeds; emits `MULTILENS_ULTRA_COMPRESSION_ROUND1_V1.json`, `ROUND2`, `DECISION`, `BASELINE_LOCK`. Not required on every commit.
- **Master codebook lexicon V1**: `scripts/core/master_codebook_lexicon_v1_bridge.py` resolves `reports/constitution/btrack_pilot/master_codebook_lexicon_v1_*_rows_latest.json` (or an explicit path) and, when `use_master_codebook_lexicon_v1=True` in `evaluate_report`, **union-matches** Unicode word tokens of each case’s `raw_text` against export `normalized_form` values to extend **must_keep** (metadata under `route.master_codebook_lexicon_v1`). Reproduce export: `py scripts/export_master_codebook_v1.py`. This is **lexicon rail join only** (no 4D vectors, no replacement of domain shard JSON policy).

- **2026-04-03 — Integrity-first token-saving gate:** `evaluate_report` may append missing `must_keep` tokens (experimental safety net), which can lower bench `global_token_saving_rate` slightly below 50%. `quality_gate` exposes both `ultra_saving_50_ok` (legacy ≥0.50) and `ultra_saving_policy_ok` / `ultra_saving_policy_min` (0.49). Remediation context: `reports/memory/mkm_memory_no_go_remediation_note_latest.json`. **`MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json` `go_no_go` is not auto-set from KPI alone.**

## 7) Terminology lock (anti-confusion)

- "12AI implemented": currently means **routing orchestration policy is active with a multi-zone shard router** (all `zone_*.json` files under `codebook/shards/`; see §1–2).
- "12AI" does **not** imply 12 subagents must run, and does **not** imply a 1:1 binding between codebook domain count and agent count.
- "Codebook": currently means shard JSON policy + template/codebook assets, not only one file.
- "4D compression": transformation engine concept used by runtime strategy path.
- "Post-it metadata": practical hint fields retained for reconstruction/evaluation context.

## 8) Change control

- If runtime path changes, update this file first, then update:
  - `docs/NotebookLM_sources_manifest.md`
  - `scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1`
  - `docs/final/openapi_token_compression_stub_v1.yaml` (when compression API contract changes)
  - `docs/final/openapi_token_compression_v2_draft.yaml` (when Trust Packet / v2 draft contract changes; §11)

## 9) Master Codebook V1 (lexicon rail snapshot) — completion rubric

- **Done means**: export JSON validates schema `master_codebook_lexicon_v1`, `row_count` matches emitted entries, `inputs` lists hashed paths for `master_atoms_morphhb_seed_latest.jsonl` and `master_atoms_lexicon_seed_latest.jsonl`.
- **Symbol key**: stable `atom_id` from master atoms; MorphHB row uses `morphhb_chosen` when present else index row only.
- **Scope (V1)**: Hebrew + Greek + other langs from atom catalog with per-row `lexicon_rail` / `morphhb_match_method`; **not** the product “14K clustered symbols” target (that is milestone 1b, separate plan).
- **Filename**: use `master_codebook_lexicon_v1_{row_count}_rows_latest.json` under `reports/constitution/btrack_pilot/` (avoid fixed `14K` in the name until cardinality is SSOT).
- **Reproduce**: `py scripts/export_master_codebook_v1.py` after `map_master_atoms_morphhb_seed.py` and optional `resolve_morphhb_multi_deterministic.py --write-latest`.

### 9.1 Token API data contract (hydration SSOT)

- **v2 draft (Trust Packet, not implemented):** `docs/final/openapi_token_compression_v2_draft.yaml` — see §11.
- **Canonical spec (current stub):** `docs/final/openapi_token_compression_stub_v1.yaml` — `api_contract_version` (HTTP shape semver), optional `eval_context` (paths/hints aligned with §6.1 inputs such as `MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json`), optional `hydration_hints.atom_ids` for future symbol↔row join (Master Codebook V1 `atom_id`; **no 4D vectors in this contract**).
- **Stub**: `scripts/compression_token_api_stub.py`; `compression_metrics` can be populated by live eval (`metrics_mode=live`) or decision fallback (`metrics_mode=decision_fallback`).
- **Version bump rule**: PATCH=docs/examples only, MINOR=additive backward-compatible fields, MAJOR=required field change/removal or behavior-breaking contract change.
- **Hydration mix monitor**: `py scripts/report_token_api_hydration_mix.py` → `reports/constitution/btrack_pilot/token_api_hydration_mix_latest.json` (tracks `metrics_mode` counts and `live_ratio`).
- **KPI summary snapshot**: `py scripts/report_ultra_compression_kpi_summary.py` → `reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json` (decision/quality/perf/hydration in one JSON).
- **3-mode demo runner (PowerShell)**: `pwsh -File scripts/demo_token_api_modes.ps1` (none/decision_fallback/live + expand roundtrip).

## 10) External pilot communication (single-page fact-lock)

Use this section (plus `docs/final/openapi_token_compression_stub_v1.yaml` info block) as the **only** agreed talking points for pilots/partners. Do not duplicate a separate long narrative doc.

- **POST /v1/compress**: Domain router (`scripts/core/domain_router.py` + shard JSON) **always** runs on real code. `compression_metrics` is absent unless `eval_context.hydrate_metrics` is true. When `hydrate_live_eval` is true, the stub calls `evaluate_report` (same family as multilens benches); on exception it may set `integrity_flags.hydration_live_eval_failed` and fall back to decision-artifact estimates when available.
- **POST /v1/expand**: **Echo** of `original_text` from the payload (`stub_expand`, `lossless_echo`); not a residual/patch decompressor. Partners must not assume lossless “telegram decode” semantics beyond echo; treat submitted text as sensitive for logging.
- **Multi-lens / 16-state**: Multi-lens remains a **validation/eval** layer in the bench path, not “the compressor.” Myeongri / 16-state is **not** a mandatory runtime wire in this HTTP stub (see §4).

Onboarding checklist for pilots: (1) default compress returns **router + flags only** unless hydration flags are set; (2) cite **bench JSON artifacts** for savings numbers, not illustrative UI demos; (3) never claim “production SaaS” for this stub without separate auth/SLA scope.

## 11) HTTP v2 (planned): Trust Packet API contract & SLA boundaries

**Status:** OpenAPI draft + **experimental FastAPI stub** (`scripts/compression_token_api_v2_stub.py`, e.g. port 8011). Uses `GlobalPivotCompressionPipeline` for packet payload — **not** a committed production SLA; v1 stub remains the default for light pilots.

**SSOT file:** `docs/final/openapi_token_compression_v2_draft.yaml` (`info.version` tracks draft iterations).

**Intent:** Move from v1 “compress envelope + expand echo” to a **single round-trip artifact** — `compression_packet` — that carries `compressed_text` and structured `residual_meta` so `POST /v2/expand` can reassemble using the same packet (wire `GlobalPivotCompressionPipeline`-class logic when implemented). v1 stub remains the reference for current pilots.

**Principles (fact-locked for future implementation):**

1. **Packet versioning:** Every packet includes `packet_format_version` and `api_contract_version` so older clients and engines remain distinguishable.
2. **Loss profile:** Request/response use `loss_profile` (`lossless_text` | `semantic_general` | `code_equivalent`) so marketing does not confuse “token savings” with “build equivalence” for code.
3. **Stateless server:** Default assumption — **no server-side storage** of full originals; the client holds `compression_packet` (still **sensitive** — TLS + client key discipline). Deviations require explicit product tier and legal review.
4. **SLA boundary:** Auth, rate limits, retention, regional deployment — **out of scope** until a separate operations doc references this contract.

**Phase alignment (roadmap, not implemented):** Phase 1 = packet schema + compress response shape; Phase 2 = expand input = packet only + reassembly; Phase 3 = strict mode routing (`code_equivalent` ↔ `CodingBinaryNitroCompressor` path) isolated from general semantic path.

**Change control:** When changing v2 behavior, update this section, `openapi_token_compression_v2_draft.yaml`, and the stub module; keep v1 stub for regression until deprecation policy is written.

Status: Fact-Lock active (2026-03-31); §11 stub implementation noted (2026-04-01).
