# Unified-Intelligence — 통합 전황판 (메인 지휘 SSOT)

**작성일**: 2026-03-29  
**역할**: 이 채팅 = **메인 지휘 터미널**. 병렬 창 산출은 **파일·Git·`docs/NotebookLM_sources_manifest.md`**로만 합류; 긴 채팅 덤프만으로 병합하지 않는다.

---

## 한 표 요약

| 축 | 팩트 앵커 | 경로 | 검증 / 비고 |
|----|-----------|------|-------------|
| **A1 — 16-State “최소 k” 커버리지 탐사** | Master Probe v1: `coverage_summary.states_with_audit === 16` | `data/myeongni/16_STATE_MASTER_PROBE_v1.json` | 정본 JSONL `data/myeongni/myeongni_16_state_experiment_20260329.jsonl`; 집계 `scripts/myeongni_summary_gen.py` |
| **Phase 1 — 디지털 청문회 (Logos 근원)** | `logos_layered_search` **Phase 1**: 정경(canon) 스트리밍·힙 순위·`canon_top_k` 상한 | `tools/core/logos_layered_search.py` · `docs/final/LOGOS_RISK_BRIDGE_v1.md` §1 | 회귀 `tests/test_logos_layered_search.py`; 모듈은 `data/regimes/`·금융 API를 import하지 않음 (Logos-first) |

---

## 슬롯 (병렬 창·배치 완료 시 기입)

| 항목 | 값 |
|------|-----|
| **Git 커밋 (short)** | `c887d27d6f` — `feat(myeongni): add all-states master probe verification suite` 포함 (full: `c887d27d6f97b8d12b2f1769277ed3e61fb80ed1`) |
| **Vault `sync_notebooklm_sources_to_mkm_data_vault.ps1` exit** | `0` — `copied=45` `skipped=0` → `G:\공유 드라이브\MKM_DATA_VAULT\vault\notebooklm_sources` |
| **관련 pytest 스코프** | `py -m pytest tests/test_logos_layered_search.py -q` → exit `0` (2 passed, ~2s) |
| **Master Probe 전수 검증 (Fact-Lock)** | `py scripts/verify_master_probe_all_states.py` → exit `0` (149/149 Pass, reproducibility 100%) |
| **Master Probe pytest** | `py -m pytest tests/test_verify_master_probe_all_states.py -q` → exit `0` |

---

## 병합 규칙 (요약)

- **NotebookLM / A·B SSOT**: `docs/NotebookLM_sources_manifest.md` — 내용 충돌 시 **메인 지휘 창에서만** 편집.
- **병렬 창**: 대용량 `grep`·장시간 스크립트·단일 파일 디버그·읽기 전용 탐색; **매니페스트 직접 편집 금지** (보고만).

---

## 상호 참조

- 헌법 구현 팩트: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`
- Logos 근원 선행: `.cursor/rules/logos-first-pipeline.mdc`

**상태**: Fact-Lock 완료 (2026-03-29) — Master Probe 검증 스크립트·테스트는 `c887d27d6f`에 기록됨; 수치·해시 추가 변경 시 위 슬롯만 갱신.
