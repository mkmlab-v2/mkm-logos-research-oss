# LG HS Before/After — Fact-Lock (v1)

**Generated:** `2026-05-16T06:54:50Z` · **Status:** `[DRAFT]` internal only

## Verdict summary

| Claim | Verdict |
|-------|---------|
| `export_not_found_80` | **PARTIAL_TRUE_REWORD_REQUIRED** |
| `lexicon_41775` | **FACT** |
| `policy_floor_047` | **FACT** |
| `cmp2_014_health` | **FACT_WITH_BASELINE_LABEL** |
| `simulation_7680` | **FAIL_DO_NOT_USE** |
| `safety_plc_complete` | **HYPO_DRAFT_ONLY** |

## Safe copy table (LG-facing)

| Axis | Before | After |
|------|--------|-------|
| Bench cases | 40-case eval; codebook export often missing → export_not_found per case path | 40-case eval; lexicon 41775 terms; 0 export_not_found in frozen active report |
| Policy floor | 0.49 floor chase; many HOLD experiments (W4–W9 archive) | 0.47 published floor; ~47.1% saving; avg Jaccard ~0.885 |
| cmp2_014 (health) | Jaccard 0.625 (bridge policy report snapshot) | Jaccard 0.875 (baseline sweep health_case) |
| Governance narrative | Compression tool framing | Artifact-bound discipline + optional Safety PLC narrative [DRAFT] |

## Do not say externally

- 7,680 hardware sweeps (use round2 grid **332** / evaluated **108** if needed)
- export_not_found **80 cases** (say **40-case bench** or **codebook export was missing**)
- Safety PLC certified / legal alibi complete / already won

JSON SSOT: `docs/final/artifacts/lg_hs_before_after_factcheck_v1_latest.json`
