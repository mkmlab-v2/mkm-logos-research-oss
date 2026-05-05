# 중간 레이어 다중 렌즈 — 작업 리스트 (B-track 정합)

**작성일**: 2026-03-30  
**상위 SSOT**: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` (Multi-Lens·격벽·TOE 비단정)  
**목적**: 단일 “통합장 완성”이 아니라, **렌즈별 격벽을 유지한 채** 아티팩트·테스트·문서·CI가 **같은 사실**을 가리키게 만드는 **중간 레이어** 정합 절차를 정리한다.

---

## 완료 정의 (이 문서의 “끝”)

- **여기서 끝**: B-track 벤치·가설·관측이 **저장소 경로·pytest·CI**로 재현 가능하고, **실매매·OOF·A-track 자동 합선**이 없다.
- **여기서 끝 아님**: 상용 승격, 처방 엔진 합선, 단일 수학적 TOE 선언 — **Promotion Loop·별도 PR** 영역.

---

## Phase 1 — CROSS_REF (정경 ↔ 위성 ↔ `state_id`)

| # | 작업 | 상태 | 비고 |
|---|------|------|------|
| 1.1 | `docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json` 행 수·`canonical_ref` ↔ `LOGOS_STATE_MAPPING_V1` | [x] | 회귀: `tests/test_cross_ref_dss_schema.py` |
| 1.2 | `docs/final/CROSS_REF_DRAFT_V2_DOCUMENT.schema.json` + jsonschema 검증 | [x] | 동일 테스트 내 `test_cross_ref_draft_validates_against_json_schema` |
| 1.3 | `docs/final/btrack_phase3_cross_ref_snapshot.md` — SSOT와 동일 ENTRY·코드펜스 | [x] | 백틱·`disclaimer` 많을 때 **닫는 펜스**만으로 자르지 말 것 |
| 1.4 | 대규모 수정 시: **JSON을 SSOT로 편집 → 스냅샷 펜스 갱신** | [x] | `py scripts/sync_btrack_phase3_snapshot_json_fence.py --apply` 후 `pytest tests/test_cross_ref_dss_schema.py` |

---

## Phase 2 — 사상·명리 벤치 (Timing / Vessel)

| # | 작업 | 상태 | 비고 |
|---|------|------|------|
| 2.1 | `docs/final/artifacts/SASANG_CROSS_REF_DRAFT.json` + 청크 테이블 조인 | [x] | `tests/test_sasang_cross_ref_draft.py` |
| 2.2 | `data/myeongni/insight_observation_log*.jsonl` + `MYEONGNI_FUSION_INTERFACE_STUB.json` | [x] | `tests/test_myeongni_insight_observation_log.py` (파일 추적은 팀 정책) |
| 2.3 | `docs/final/MYEONGRI_INSIGHT_SSOT.md` — §1.2 대운·세운 테이블 표 | [x] | 확정 경로는 표 첫 행에 추후 기입; 미확정은 `—`·`[HYPO]` |

---

## Phase 3 — CI · 로컬 번들 (Fact-Lock)

| # | 작업 | 상태 | 비고 |
|---|------|------|------|
| 3.1 | `.github/workflows/dual-regime-integrity.yml` — dual-regime + workspace + myeongni 순서 | [x] | `integrity_guard` 포함 |
| 3.2 | `run_prophecy_alignment_pytest.ps1` / `.sh` — **CI 워크스페이스 테스트와 동일 목록** | [x] | logos + CROSS_REF + ENTRY16 source-hunt(log+summary) + SASANG + myeongni insight + 4-grid myeongri·sasang compression spike |

---

## Phase 4 — 운영 · Promotion 경계

| # | 작업 | 상태 | 비고 |
|---|------|------|------|
| 4.1 | B-track `note`·`[HYPO]` — ENTRY_11 패턴 유지 | [x] | `CROSS_REF`·NL 반증 박제 |
| 4.2 | A-track·실매매·트레이딩 로더 — **본 경로 기본 로드 금지** (CONSTITUTION §4·§8) | [x] | 정책 문서; 승격 시 PR |
| 4.3 | NotebookLM / vault — **중복 소스 제거**, `docs/NotebookLM_sources_manifest.md` 준수 | [x] | `-WhatIf` 점검: 중복 0건 (2026-03-30) |
| 4.4 | `ENTRY_07/08/16` 외부 판본 대기 큐 운영 전환 | [x] | `docs/final/CROSS_REF_CITATION_ANCHOR_EVIDENCE_CHECKLIST_2026-03-30.md`의 "외부 판본 대기 큐" 섹션 참조 |
| 4.5 | 대기 큐 모니터링 주기 고정(월 1회/소스 공지 이벤트) | [x] | 대기 큐 재시도는 신규 근거 소스 등장 시에만 실행 |
| 4.6 | 월간 점검 명령 템플릿 고정 | [x] | 체크리스트에 Windows 실행 템플릿 추가 |
| 4.7 | 월간 점검 스크립트 옵션(`-SkipBundle`) 운용 규칙 명시 | [x] | 정기 점검=기본(번들 포함), 이벤트 직후 1차 확인=옵션 허용 |
| 4.8 | 월간 점검 실행 로그(JSONL) 누적 운영 | [x] | `docs/final/artifacts/waiting_queue_monthly_check_log.jsonl`에 skip/full 1회 이상 기록 |
| 4.9 | 월간 점검 후 ENTRY16 summary 계약 테스트 유지 | [x] | `tests/test_entry16_source_hunt_summary.py`로 출력 계약 고정 |
| 4.10 | ENTRY16 승격 게이트 리포트/계약 테스트 유지 (Direct + Proxy Manual 경로) | [x] | `scripts/evaluate_entry16_promotion_gate.py` + `tests/test_entry16_promotion_gate.py` |

---

## Phase 5 — 선택 (자동화)

| # | 작업 | 상태 | 비고 |
|---|------|------|------|
| 5.1 | `CROSS_REF` JSON → `btrack_phase3_cross_ref_snapshot.md` 코드펜스 덤프 | [x] | `scripts/sync_btrack_phase3_snapshot_json_fence.py` |
| 5.2 | `multi_corpus_policy` / 격벽 테스트 — 위성 코퍼스 추가 시 확장 | [x] | `tests/test_multi_corpus_isolation_policy.py`; 증거 수집표: `docs/final/CROSS_REF_CITATION_ANCHOR_EVIDENCE_CHECKLIST_2026-03-30.md` |

---

## 한 번에 돌리는 명령 (Windows)

저장소 루트에서:

```powershell
# CI와 유사 순서(Windows): integrity_guard → prophecy 번들 → … → 사상 통찰 번들 pytest → Bio n-states 재수화 pytest → MKM Trinity 인덱스(jsonschema) pytest → 일일 실행 인사이트 브리프 pytest (dual-regime 정렬)
powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\run_fact_lock_bundle.ps1
```

번들만(스모크+Fact-Lock, integrity 생략 시 `-SkipIntegrityGuard`):  
`Set-Location C:\workspace\projects\bitcoin-trading` 후 `.\ops\v2\tasks\run_prophecy_alignment_pytest.ps1`.

`dual-regime-integrity`와 동일한 워크스페이스 테스트를 포함하려면 위 스크립트가 **최신**인지 확인한다 (`CONSTITUTION` §6 표).

사상–사주 조인트 문헌·큐레이트 파이프라인(Europe PMC 픽스처·오프라인 회귀 7 + **승인 출처** `data/myeongni/curated_saju_joint_v1.jsonl` 인제스트 1)은 `run_fact_lock_bundle.ps1` **기본**에 포함된다. 생략: **로컬 번들만** `-SkipSasangSajuJointLiteraturePipeline`(GitHub `dual-regime-integrity.yml` CI 단계에는 해당 스킵 플래그 없음·전체 회귀 고정). **끝단 staleness(선택 생략):** `-SkipCuratedJointStalenessCheck` — 큐레이트 시각(`ingest_at_utc`·행 없으면 파일 mtime) vs `docs/final/artifacts/myeongni_celebrity_hit_rate_v1.json` `generated_at_utc` 24h 초과 시 `STALE` 기록 · `scripts/check_curated_saju_joint_staleness_v1.py`·`reports/curated_saju_joint_staleness_v1_latest.json`. 스크립트·데이터·pytest는 `CONSTITUTION` 표 **「사상체질↔문헌↔사주 조인트」**·동 워크플로를 본다.

---

**상태**: 내부 작업 완료 잠금 (2026-03-30, ENTRY_16 Proxy Manual 승인 반영). 재개 트리거는 `ENTRY_07/08/16` 외부 판본 업데이트 이벤트로 제한한다.

---

## 문서 라벨 규칙 (Fact-Safe)

| 라벨 | 의미 | 사용 기준 |
|------|------|-----------|
| `[FACT]` | 재현·추적 가능한 진술 | 표의 경로·워크플로·pytest·CI·아티팩트로 검증된 항목; 잠금·완료 일자가 근거와 함께 기록됨 |
| `[HYPO]` | B-track 벤치·가설 | `CROSS_REF` rationale, 명리·사상 초안 필드, 미확정 표기(`—`, TBD); 승격·합선 전까지 단정 금지 |
| `[VISION]` | 경계·로드맵 | **여기서 끝 아님** 구간, Promotion Loop·상용 승격; 목표이지 현재 구현 단정 아님 |
| `[NON-MEDICAL]` | 비의료 고지 | 명리·사상·체질 문맥이 Phase 표에 포함되므로, 대외 인용 시 의료 효능·진단 주장과 분리 |

본 작업 리스트의 Phase 표는 위 라벨로 읽는다: `[x]` 체크와 테스트·경로가 붙은 행은 `[FACT]`에 가깝고, 격벽·승격 경계 문장은 `[VISION]`, 위성 코퍼스·테이블 미기입은 `[HYPO]`다.
