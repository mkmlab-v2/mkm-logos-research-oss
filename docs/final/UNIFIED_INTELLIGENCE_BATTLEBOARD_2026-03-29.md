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
| **CI golden lock (intersection + k)** | `tests/snapshots/integrity_lock.json`: `k_top=6866` (per-regime), four-way intersection `count_all_four=1574` / list length 1574; `scripts/integrity_guard.py`가 이 값과 해시를 검증 |
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

---

## Handoff (다른 AI / 병렬 창)

**최종 갱신**: 2026-04-03 (`git rev-parse HEAD` 기준 — NotebookLM 지휘부·매니페스트 병합 규칙 준수)

| 항목 | 값 |
|------|-----|
| **브랜치** | `main` |
| **Handoff 기록 커밋 (full)** | `a630645a7c48750b8693a42db576853de9bf76e3` |
| **Handoff 기록 커밋 (short)** | `a630645a7c` |
| **SSOT 한 줄** | `a630645a7c feat(scripts): add sasang encoder smoke benchmark and HF cache gitignore` |
| **NotebookLM 작전지휘부** | 노트북 `347e5cbe-0ade-4615-9aac-8747d4fa644e` · 소스 **28**개 · 핵심: `CONSTITUTION_*`, `NotebookLM_sources_manifest.md`, 본 전황판, `AGENTS.md`/`CLAUDE.md`, `P0_COMMERCIALIZATION_TRACKER.md` |
| **작업트리** | 화이트리스트 경로는 커밋됨. 실험 트리는 `.gitignore`의 `projects/*` 등으로 **미표시**될 수 있음 — 로컬은 `git status`로 확인. |

> **운영 규칙 (융합)**: 저장소 **진짜 팁**은 항상 터미널의 `git rev-parse HEAD`가 SSOT. 위 표의 해시는 “이 Handoff 블록을 마지막으로 맞춘 커밋”이며, Handoff만 수정하는 커밋을 내면 그 직후 새 객체 해시가 생기므로 **표는 최신 팁보다 한 커밋 늦을 수 있음(정상)**. 매번 표를 최신 `HEAD`에 맞출 필요는 없고, 필요할 때만 갱신하면 된다. 완전 일치가 필요하면 해당 커밋 직후 표를 한 번 더 고치거나, 검증은 `git rev-parse HEAD`만 보면 된다.

**수정됨 (M)**  
없음 (위 HEAD에 반영됨; 전황판만 편집 직후에는 잠깐 M일 수 있음 → 커밋으로 정리)

**추적 안 됨 (??)**  
`docs/external_research/`·레짐/Logos/명리 보조 스크립트 묶음은 **main 추적 완료** (2026-03-29 Workspace-Purge). 로컬 다앱·랜딩 트리는 `.gitignore`의 `projects/*` 블록 — `git status`에 미표시.

**Next**  
- SSOT만 유지: 실험 파일은 브랜치·stash로 분리하거나 `git restore`로 정리.  
- 실험선을 커밋할 때는 화이트리스트 확정 후 `git add`·커밋 (동일 파일 동시 편집 주의).
