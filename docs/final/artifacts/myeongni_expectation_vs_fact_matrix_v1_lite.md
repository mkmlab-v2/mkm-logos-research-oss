# 명리 — 기대치 vs 디스크 팩트락 (U3-lite)

- **schema:** `myeongni_expectation_vs_fact_matrix_v1_lite`
- **version:** `1.0.0`
- **rail:** `B_TRACK` · **send_gate:** `HOLD`
- **full_inventory:** deferred (U3-full)

## 매트릭스 (lite)

| row | 기대 (`[HYPO]`) | 팩트 (`[FACT]`) | 격벽 |
|-----|----------------|----------------|------|
| M1 | 명리 16상 = 사상 12셀 identity | `myeongni_16_state` 실험 JSONL ≠ `sasang_persona_grid_v1` | identity map **금지** |
| M2 | 출생 없이 사주·대운 단정 | `run_saju_global_birth_v1` → `build_myeongni_full_report_v1` | 추측 단정 **금지** |
| M3 | 학파 충돌 = Track A GO | `myeongni_conflict_arbitration_*` 관측·B-track | 실매매·승격 **금지** |
| M4 | 시장 일진 = 개인 사주 치환 | `market_myeongni_lens` 별도 레인 | 자동 치환 경로 **없음** |

## Read 순서 (high_res)

1. 본 lite 매트릭스
2. `docs/final/artifacts/MYEONGNI_INDEPENDENT_LENS_V0_CONTRACT.json`
3. `docs/final/artifacts/myeongni_independent_lens_latest.json`
4. `reports/myeongni_conflict_arbitration_runtime_mode_latest.json` (있을 때)

## 재현

`py scripts/run_lens_myeongni.py` · `py scripts/build_myeongni_full_report_v1.py`
