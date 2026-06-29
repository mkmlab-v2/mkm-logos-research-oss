# 성경 Logos — 기대치 vs 디스크 팩트락 (U3-lite)

- **schema:** `logos_expectation_vs_fact_matrix_v1_lite`
- **version:** `1.0.0`
- **rail:** `B_TRACK` · **send_gate:** `HOLD` · **gating:** `[NON_GATING]`
- **full_inventory:** deferred (U3-full)

## 매트릭스 (lite)

| row | 기대 (`[HYPO]`) | 팩트 (`[FACT]`) | 격벽 |
|-----|----------------|----------------|------|
| L1 | Logos = 실매매·예언 트리거 | `logos_independent_lens` + GraphRAG 체인 · gold eval | `[NON_GATING]` · Track A **금지** |
| L2 | 게마트리아 = 사상 stress 합선 | `gematria_bridge_v1` 정적 커널 · sidecar `routing_hints_only` | `vector_4d` 합선 **금지** |
| L3 | NL “완벽 통합·0% 환각” = SSOT | `notebooklm_lens_logos_nl_fact_lock_guard_v1` | NL 단독 **금지** |
| L4 | 666·금융 앵커 자동 결합 | gold spot · pre-reg | 가짜 앵커·묵시 결합 **금지** |

## Read 순서 (high_res)

1. 본 lite 매트릭스
2. `docs/final/artifacts/LOGOS_INDEPENDENT_LENS_V0_CONTRACT.json`
3. `docs/final/artifacts/logos_independent_lens_latest.json`
4. `docs/final/artifacts/notebooklm_lens_logos_nl_fact_lock_guard_v1_latest.md`

## 재현

`py scripts/run_lens_logos.py`
