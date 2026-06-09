# Multi-Res Index — drift recovery drill v1

**Track:** B · `[HYPO]` · `research_only`  
**Purpose:** Operator drill when low-res index SHA drifts from high-res source.

## Trigger

- `check_mkm_ops_memory_must_keep_gate_v1.py` reports missing tags after overlay merge, **or**
- `prism_ops_fills_multi_res_summary` `content_sha256_prefix` differs from live JSON slice.

## Steps (local)

1. `py scripts/multi_res_fills_join_v1.py` — rebuild `reports/multi_res_fills_index_v1_latest.json`
2. `py scripts/build_mkm_ops_memory_fills_overlay_v1.py` — merge fills overlay into ops index
3. `py scripts/check_mkm_ops_memory_must_keep_gate_v1.py --phase source`
4. `py -m pytest tests/test_multi_res_drift_recovery_drill_v1.py -q`

## Rollback

- `git restore storage/meta/mkm_ops_memory_index_v1.json` (if committed snapshot undesired)
- Re-run `py scripts/build_mkm_ops_memory_index_v1.py` for base index without fills overlay

## Never

- Do not write `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`
- Do not enable live trading or apply-active from this drill
