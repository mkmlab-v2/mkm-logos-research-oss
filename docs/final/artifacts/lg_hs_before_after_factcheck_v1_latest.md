# LG HS Before/After — Fact-Lock (v1)

**Generated:** `2026-05-18T21:38:12Z` · **Status:** `[DRAFT]` internal only

## Verdict summary

| Claim | Verdict |
|-------|---------|
| `export_not_found_80` | **PARTIAL_TRUE_REWORD_REQUIRED** |
| `lexicon_41775` | **FACT** |
| `policy_floor_047` | **FACT** |
| `cmp2_014_health` | **FACT_WITH_BASELINE_LABEL** |
| `simulation_7680` | **FAIL_DO_NOT_USE** |
| `safety_plc_complete` | **HYPO_DRAFT_ONLY** |
| `domain_table_per_shard_saving` | **FAIL_DO_NOT_USE** |
| `domain_table_scm_avg_067` | **FAIL_DO_NOT_USE** |
| `domain_table_timing_091` | **FAIL_DO_NOT_USE** |
| `shadow_auditor_17_of_17` | **FAIL_DO_NOT_USE** |
| `bench_conc10_as_production_sla` | **PARTIAL_TRUE_REWORD_REQUIRED** |
| `jaccard_equals_meaning_percent` | **FAIL_DO_NOT_USE** |
| `multi_shard_simultaneous_activation` | **FAIL_DO_NOT_USE** |
| `plugin_lora_zero_training_cost` | **FAIL_DO_NOT_USE** |
| `zone_c_health_filename` | **FAIL_DO_NOT_USE** |
| `plugin_shard_single_route` | **FACT** |

## Safe copy table (LG-facing)

| Axis | Before | After |
|------|--------|-------|
| Bench cases | 40-case eval; codebook export often missing → export_not_found per case path | 40-case eval; lexicon 41775 terms; 0 export_not_found in frozen active report |
| Policy floor | 0.49 floor chase; many HOLD experiments (W4–W9 archive) | 0.47 published floor; ~47.1% saving; avg Jaccard ~0.885 |
| cmp2_014 (health) | Jaccard 0.625 (bridge policy report snapshot) | Jaccard 0.875 (baseline sweep health_case) |
| Governance narrative | Compression tool framing | Artifact-bound discipline + optional Safety PLC narrative [DRAFT] |

## LG-safe shard Jaccard (frozen active report)

| Label | n | avg Jaccard | min Jaccard | token saving |
|-------|---|-------------|-------------|--------------|
| Global (40-case bench) | 40 | 0.890 | 0.714 | 47.54% |
| zone_a_scm | 12 | 0.910 | 0.733 | (global only — not per-shard) |
| zone_b_timing | 2 | 0.845 | 0.786 | (global only — not per-shard) |
| zone_c_hangul | 14 | 0.903 | 0.750 | (global only — not per-shard) |
| zone_d_ssot | 8 | 0.834 | 0.714 | (global only — not per-shard) |
| zone_g_health | 4 | 0.922 | 0.875 | (global only — not per-shard) |

## Governance proofs (accurate wording)

- **Lexicon:** 41,775 terms frozen (`master_codebook_lexicon_v1_41775_rows_latest.json`).
- **Shadow Auditor:** artifact contract pytest (**4 tests**, not 17/17) + KPI/active scan; optional `--refresh-bench` for full re-run.
- **Latency:** `bench_l1_api_load_conc10` = local loopback, conc10, ~500 words — **not** production SLA; VPS p95 ~665–847 ms (2026-05-16 triplet). **Do not** link ms to token saving (`correlation_claim_allowed: false`).

## Do not say externally

- 7,680 hardware sweeps (use round2 grid **332** / evaluated **108** if needed)
- export_not_found **80 cases** (say **40-case bench** or **codebook export was missing**)
- Safety PLC certified / legal alibi complete / already won
- **Per-shard 47% saving** (saving is global on 40-case bench only)
- **SCM domain average 0.667** (use: scm min ~0.667, scm avg ~0.866, global min 0.667)
- **Timing ~0.910** (use ~0.845 on 2 timing cases)
- **Shadow Auditor 17/17 passed** (use **4 contract tests passed**)
- **의미 89% 복원** (use **avg Jaccard ~0.885 proxy**)
- **conc10 45/980 ms = 양산 보드 SLA** (cite environment + fail vs 200ms target; prefer VPS triplet for external RTT)

JSON SSOT: `docs/final/artifacts/lg_hs_before_after_factcheck_v1_latest.json`
