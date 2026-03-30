# Constitution / Inference — 구현 팩트 (SSOT)

**작성일**: 2026-03-29  
**목적**: “기획·NotebookLM·헌법 문서만 보고 구현됨”이라고 단정하지 않도록, **호출 가능한 경로**와 **검증 상태**를 한곳에 고정한다.

---

## 1. 검증 범위

- **포함**: 저장소 내 실제 파일 경로, 스모크/단위 테스트에서 참조되는 심볼.
- **제외**: 다른 브랜치·미커밋 로컬 전용 파일·외부 Vault만 존재하는 산출물 (경로만 “확인 필요”로 표기).

### 1.1 엔지니어링 정체성 (Multi-Lens · 단일 방정식 비단정)

**폐기(선언·단정 금지):** 성경·명리·시장·외경·DSS 등을 **물리 만물이론(TOE)급 단일 방정식**으로 이미 합선·구현했다는 서술. 기획서·NotebookLM·수사만으로 **“통일장 완성”**을 코드에 대입하지 않는다.

**채택(Fact-Lock):**

- **다중 렌즈:** 로고스(정경 코어), 명리(B-track 실험), 레짐·PSI(실물 1차) 등은 **각각의 스키마·경로**로 두고, 필요 시 **교차 참조·관측 리포트**로만 맞춘다.
- **격벽:** §4 평행 코퍼스, §3 명리 분리, §2.1 dual-regime(16상 캡 미연동)을 **합선 방지**의 기본으로 둔다.
- **UFT·통일장 라벨:** `tools/core/unified_field_theory_engine*.py` 등은 **§10 경로 팩트**로만 인용한다. **호출 가능한 `.py`·테스트**가 없으면 “구현됨”으로 말하지 않는다(본 문서 상단 목적과 동일).

---

## 2. Dual-regime / 레짐 융합 (실물 쪽, 1차 레짐)

| 항목 | 경로 | 비고 |
|------|------|------|
| HTTP/진입점 | `projects/bitcoin-trading/src/integration/dual_regime_api.py` | FastAPI 앱, `/dual-regime` 등 |
| 정책 SSOT | `data/regimes/regime_fusion_policy.json` | 워크스페이스 상대 경로로 로드 |
| 보조 정책 | `data/regimes/dual_regime_policy.json` | 존재 확인됨 |
| 레짐 맵 | `data/regimes/regime_map.json` | 존재 확인됨 |
| 성경 2차 레짐 | `data/regimes/biblical_regime_matrix.json` | 헌법: 보조 레이어 |

### 2.1 Dual-regime 평가 하이브리드 (연속 캡 · 이산 임계 · 16상 미연동)

`projects/bitcoin-trading/src/integration/dual_regime_api.py`의 `evaluate_dual_regime_and_market_shock` 팩트:

- **연속(실수):** `stress`, `risk_multiplier_cap`; 선택적 로고스 브리지에서 `resonance`·조정 캡.
- **이산/임계:** `psi_thresholds`(warning/crisis), `market_shock_confirmed`, `veto_triggered`; `resonance_count`는 4D 축이 중립(0.25)에서 벗어난 개수(0–4 정수).
- **명리 16상(B-track):** `state_id`로 캡을 분기하지 않음. `get_myeongni_16_state_experiment_ssot`는 **경로·메타**만 노출하며, 16상 실험 JSONL·스키마는 **캡 합선 전** Fact-Lock(§3.1)과 동일 정책.

**정체성:** 단일 “통일장 방정식”으로 모든 도메인을 합선했다고 단정하지 않는다. 레짐·로고스·명리는 **별 모듈·별 격벽**을 유지하고, 본 절은 **벤치용 dual-regime 조합기**의 실제 동작만 기술한다.

---

## 3. 명리(Myeongri) 분리 네임스페이스 (거래 그래프와 합선 방지)

| 항목 | 경로 | 비고 |
|------|------|------|
| 명리 전용 ledger 접두어 | `projects/bitcoin-trading/ops/v2/memory/decision_ledger.py` | `MYEONGRI_LEDGER_PREFIX`, `append_myeongri_decision_ledger` |
| Fact-lock 스냅샷 | `projects/bitcoin-trading/ops/v2/memory/fact_lock_snapshot.py` | `trading_config` 내 `myeongri` 서브셋 + 정책 해시 |

### 3.1 16-상태 실험 JSONL (B-track, Fact-Lock)

| 항목 | 경로 | 비고 |
|------|------|------|
| JSON Schema | `docs/final/MYEONGNI_16_STATE_EXPERIMENT_JSON_SCHEMA.json` | `state_id` 1–16; 선택 필드 `consistency_rate`, `self_contradiction_rate` (각 0–1) |
| Ledger·검증 CLI | `scripts/myeongni_16_state_experiment_ledger.py` | `append_*`, `validate-sample --path …` |
| 정본 예시 데이터 | `data/myeongni/myeongni_16_state_experiment_v1.jsonl` | 운영 적재 전 참조 |
| 샘플 (동일 스키마) | `data/myeongni/myeongni_16_state_experiment_v1.sample.jsonl` | 스텁·가설 티어 B용 |
| 단위 테스트 | `tests/test_myeongni_16_state_experiment_ledger.py` | 스키마 검증·rate 구간 |

### 3.2 Logos–명리 16상태 할당 (B-track, 스냅샷)

| 항목 | 경로 | 비고 |
|------|------|------|
| 할당 CLI | `scripts/join_logos_verses_myeongni_states_4d.py` | `scipy.linear_sum_assignment`; 입력: `backtest_results/sweep_kmin_refine/LOGOS_RESONANCE_BTC_EXT_ABSOLUTE_TOP16.json`, `data/myeongni/16_STATE_MASTER_PROBE_v1.json`, `data/logos/verse_4pipeline_full_31102.json` |
| 추적 스냅샷 | `docs/final/artifacts/LOGOS_STATE_MAPPING_V1.json` | 커밋 시점 고정; 재실행 시 `LOGOS_STATE_JOIN: total_cosine_sum=…` 로그 |
| CI 회귀 | `tests/test_logos_state_mapping_v1_snapshot.py` | 스키마·16건·`total_cosine_sum`/`mean_cosine_per_pair` 수치 고정 (**러너에서 전체 재계산 아님** — `verse_4pipeline_full_31102.json` 대용량·미추적 가능) |

### 3.3 명리 통찰 작업 (B-track, 채팅·연구 순서)

| 항목 | 경로 | 비고 |
|------|------|------|
| 작업 순서·용어·금지선 SSOT | `docs/final/MYEONGRI_INSIGHT_SSOT.md` | 0→7 단계; 융합 중간레이어와 역할 분리 |
| 관측 로그 샘플 | `data/myeongni/insight_observation_log.sample.jsonl` | `myeongni_16_state_experiment` JSONL과 별도; 통찰 전용 |
| 관측 로그(부트스트랩) | `data/myeongni/insight_observation_log.jsonl` | 주간 append; 회귀와 동일 계약 |
| 융합 인터페이스 스텁 | `docs/final/MYEONGNI_FUSION_INTERFACE_STUB.json` | `myeongni_fusion_interface_stub_v1` |
| 계약 테스트 | `tests/test_myeongni_insight_observation_log.py` | sample·log JSONL + 스텁 JSON |

**Fact-Lock**: 16상태 확장 가설은 **트레이딩 엔진 합선 전** 본 JSONL·스키마로만 기록; `dual_regime_api.py`와의 연결은 별도 승인·PR에서 명시한다.

---

## 4. Multi-Corpus Isolation Policy (평행 코퍼스)

**목적**: 정경(Logos 코어) SSOT와 사해(DSS)·70인역(LXX)·외경 등 **다른 전통**을 코드·데이터에서 혼동하지 않도록 격벽을 문서로 고정한다. 구절 간 유사도·교차 분석은 **참고 지표**일 수 있으나, 레짐·실매매 **트리거**로의 승격은 본 문서·코드북·PR에서만 허용한다.

### 4.1 레이어 정의

| 구분 | 역할 | 비고 |
|------|------|------|
| **Core (A-track)** | MT 기반 정경 31,102 구절 파이프라인 | SSOT: `data/logos/verse_4pipeline_full_31102.json` (§3.2) |
| **Satellites (B-track)** | DSS, LXX, 외경/위경 등 | **별도 파일·별 인덱스**; 코어와 row-level merge 금지 |

### 4.2 메타데이터·실행 격벽 (정책)

- 위성 코퍼스 레코드에는 출처 식별 필드를 강제한다 (예: `corpus_type` — `canonical` / `dss` / `apocrypha` / `pseudepigrapha`; `tradition` — `MT` / `LXX` / `Qumran` 등).
- 교차 분석·CLI는 **명시 옵션**(예: `--include-satellites`)이 없으면 **canonical만** 대상으로 한다.

### 4.3 단방향 산출물 (비침습)

- 위성 텍스트에서 16상·거리 등을 **측정**한 결과는 `LOGOS_STATE_MAPPING_V1.json` 등 코어 스냅샷을 **덮어쓰지 않고**, `CROSS_REF_*` 형태의 **독립 관측 리포트**로만 둔다.
- B-track 관측을 `dual_regime_api`·실매매 경로에 합선하려면 **별도 승인·PR**에서 명시한다 (§3.2·§8 Promotion Loop와 동일 취지).

### 4.4 구현 상태

| 항목 | 경로 | 비고 |
|------|------|------|
| 격벽 헬퍼 (canonical default guard) | `tests/multi_corpus_policy.py` | `iter_canonical_only`, `cross_ref_artifact_name` (CI 추적용; `tools/` 로컬 제외와 무관) |
| 위성 더미 (B-track 스모크) | `tests/fixtures/logos_satellite_dummy_one_verse.json` | 단일 구절; 코어와 병합 시 기본 가드에서 제외 |
| 단위 테스트 | `tests/test_multi_corpus_isolation_policy.py` | §4 정책 회귀 |

- DSS/LXX 등 전용 `verse_4pipeline_*.json` 또는 별 인덱스 **운영 경로**가 생기면 **본 표에 행을 추가**한다.

### 4.5 CROSS_REF 데이터 계약 (v1-Draft)

정경(A-track)과 위성(B-track)을 잇는 `CROSS_REF_*` 산출물은 **코어를 덮어쓰지 않는** 독립 아티팩트이며, 행 단위로 아래 **데이터 계약**을 따른다 (필드명은 JSON에서 `snake_case` 권장).

| 필드 | 의무 | 설명 |
|------|------|------|
| `canonical_ref` | 권장 | 정경 측 고유 식별자(예: `verse_id`). A-track만 연결할 때는 비울 수 없음. |
| `satellite_ref` | 권장 | 위성 측 고유 식별자(예: DSS 조각·외경 절 표기). |
| `corpus_type` | 필수 | `dss` / `apocrypha` / `pseudepigrapha` / `myeongni_probe` 등. |
| `link_type` | 권장 | 연결 성격: `thematic` / `lexical` / `geometric` / `temporal` / `analogy_bench` 등(열거형 문자열). |
| `confidence` | 선택 | 0.0–1.0 실험적 점수; **헌법에 수치 Prior를 고정하지 않음**. |
| `artifact_path` | 선택 | 근거·스냅샷 파일 경로(워크스페이스 상대 경로). |
| `rationale` / `notes` | 권장 | 사람이 읽는 근거·면책(가설·비유 한정 등). |
| `note` | 선택 | 행 단위 벤치 메타(예: NL 요약·반증 유형·맥락 오염 경고·[HYPO] 승격 보류); `rationale`과 별도로 박제할 때 사용. |

**확률·Prior 정책:** 마르코프 전이행렬·베이지안 사전분포 등 **수치 Prior는 본 헌법에 고정하지 않는다.** 해당 수치는 실험 결과물·연구 노트(`docs/final/` 하위, 별도 파일명)에만 존재할 수 있으며, A-track·실매매 경로로 올리려면 **Promotion Loop(§8)·별도 승인·PR**을 거친다.

**트래킹 아티팩트:** `docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json` — `schema: cross_ref_dss_to_states_draft_v2`; 행마다 `entry_id`, `canonical_ref`(정경 `verse_id`), `satellite_ref`, `corpus_type`, `link_type`, `state_candidate_id`, `rationale`; 선택 필드 `note`(벤치 메타·NL 반증 박제 등). `canonical_ref`는 **독립 해석이 아니라** `LOGOS_STATE_MAPPING_V1.json`의 동일 `state_id` 할당 `verse_id`와 기계적으로 맞춘 값(문서 상단 `canonical_join_ssot`·`canonical_join_note`). **JSON Schema:** `docs/final/CROSS_REF_DRAFT_V2_DOCUMENT.schema.json`. 회귀: `tests/test_cross_ref_dss_schema.py`. **CI:** `.github/workflows/dual-regime-integrity.yml`에서 위 테스트 실행(`jsonschema` 포함).

### 4.6 중간 레이어 다중 렌즈 (작업 순서)

격벽을 유지한 채 B-track 아티팩트·CI·문서 정합을 점검하는 **체크리스트**는 `docs/final/MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md`에 둔다. 단일 TOE 완성 선언이 아니라, **관측·벤치·인터페이스 스텁**의 재현 가능성을 올리는 절차다. `btrack_phase3_cross_ref_snapshot.md` 코드펜스는 SSOT JSON과 어긋날 경우 `scripts/sync_btrack_phase3_snapshot_json_fence.py --apply`로 맞춘 뒤 `tests/test_cross_ref_dss_schema.py`로 검증한다.

---

## 5. 코드북 템플릿 (Dual-track)

| 항목 | 경로 | 비고 |
|------|------|------|
| 마스터 템플릿 | `docs/final/master_codebook_dual_track.template.json` | `source_refs.constitution_inference` → 본 문서 |

---

## 6. 테스트 (저장소 기준)

| 항목 | 경로 |
|------|------|
| Dual-regime 스모크 | `projects/bitcoin-trading/tests/test_dual_regime_api_smoke.py` |
| Logos–명리 매핑 스냅샷 | `tests/test_logos_state_mapping_v1_snapshot.py` |
| §4 평행 코퍼스 격벽 | `tests/test_multi_corpus_isolation_policy.py` |
| §4.5 CROSS_REF DSS 초안 | `tests/test_cross_ref_dss_schema.py` |
| ENTRY_16 소스 헌트 로그 계약 | `tests/test_entry16_source_hunt_log.py` |
| ENTRY_16 소스 헌트 요약 계약 | `tests/test_entry16_source_hunt_summary.py` |
| ENTRY_16 승격 게이트 계약 | `tests/test_entry16_promotion_gate.py` |
| 사상 벤치(SASANG ↔ 명리 앵커) | `tests/test_sasang_cross_ref_draft.py` |
| §3.3 명리 통찰 관측 JSONL·융합 스텁 | `tests/test_myeongni_insight_observation_log.py` |
| 다중 렌즈 중간 레이어 절차 | `docs/final/MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md` |

---

## 7. 데이터 부재 / 확인 필요 (단정 금지)

**확인됨 (명리 융합 스키마 SSOT)**:

- **`MYEONGNI_FUSION_DECISION_JSON_SCHEMA`**: `docs/final/MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json` — JSON Schema (draft-07) for one line of `myeongri_decision_ledger_YYYYMMDD.jsonl`. 구현: `projects/bitcoin-trading/ops/v2/memory/decision_ledger.py` → `append_myeongri_decision_ledger`.

다음은 **명칭·SITREP·기획서에 등장할 수 있으나**, 현재 워크스페이스 스냅샷에서 **단독 아티팩트로 확인되지 않음**:

- **`test_fusion_slice_gate.py`**: `projects/bitcoin-trading` 하위에서 미발견.

**NotebookLM → 공유 vault 미러(구현 확인됨)** — §7 “미확인” 목록과 혼동 금지:

| 항목 | 경로 | 비고 |
|------|------|------|
| 동기화 스크립트 | `scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1` | 저장소 루트 `scripts\` |
| 오케스트레이터 호출 | `projects/bitcoin-trading/ops/v2/reports/run_notebooklm_sync.ps1` | `C:\workspace\scripts\sync_notebooklm_sources_to_mkm_data_vault.ps1` 실행 |
| 대상 vault(로컬에서 G: 마운트 시) | `G:\공유 드라이브\MKM_DATA_VAULT\vault\notebooklm_sources\` | SSOT `docs/NotebookLM_sources_manifest.md`와 `$SourceFiles`/`$SourceDirs` 동기화 유지 |
| 실행 없이 계획만 | `-WhatIf` | 매니페스트 기반 복사 예정 나열 |
| 최소 간격 우회(오케스트레이터) | `run_notebooklm_sync.ps1 -Force` | `scheduled_guard` 최소 간격 무시·즉시 1회. 수동 재시도·테스트용; 일상 스케줄은 `-Force` 없이 |
| vault 미사용/미마운트 | — | 실제 복사 없음 또는 오류 종료(스크립트 동작에 따름) |

---

## 8. Promotion Loop (연구 → 제품)

1. **B(연구)** NotebookLM·노트에서 가설 도출.
2. **지휘관**이 스키마/코드북 반영 승인.
3. **A(제품)** 본 문서·`master_codebook_dual_track.template.json`·실제 `*.py` 경로를 갱신한 뒤에만 엔진 하드코딩.

---

## 9. NotebookLM 매니페스트·이제마 B 인벤토리 (저장소 확인됨)

공유 vault(`G:\…\vault\notebooklm_sources\`)로의 파일 미러·스크립트 호출 관계는 **§7 표**에 고정한다.

| 항목 | 경로 | 비고 |
|------|------|------|
| 소스 목록 SSOT | `docs/NotebookLM_sources_manifest.md` | `## 이제마_B_Track` — 동기화 후보·미배치·근접 참조 표 |
| 인벤토리 디렉터리 | `data/corpus/ijeoma/_inventory/` | 개별 파일명은 **매니페스트 표와 동일**하게 유지·갱신 |
| SASANG 벤치 초안 | `docs/final/artifacts/SASANG_CROSS_REF_DRAFT.json` | `schema: sasang_cross_ref_draft_v1`; 청크↔`state_candidate_id` 가설 행; 처방·dual_regime 합선 금지; 회귀: `tests/test_sasang_cross_ref_draft.py` |
| 한의 원전 인수인계(문서명) | `docs/final/KOREAN_MEDICAL_CANON_INGEST_HANDOFF_2026-03-28.md` | **현재 스냅샷에 해당 파일명 없음** — A/B 분리 원칙은 `docs/NotebookLM_sources_manifest.md` §이제마_B_Track 문단으로 인용 |
| 작전지휘부 NotebookLM | ID `347e5cbe-0ade-4615-9aac-8747d4fa644e` | 2026-03-29 `notebook_get`: `source_count` 216 |
| `OPS_ONEPAGE_STATUS_LATEST.md` | — | NotebookLM 소스 **제목**으로 존재 가능; 워크스페이스 `docs/final/OPS_ONEPAGE_STATUS_LATEST.md` **미존재** — vault 미러에는 동기화 대상에 포함되지 않을 수 있음. 상세는 `docs/NotebookLM_sources_manifest.md` §작전지휘부 |

---

## 10. 통일장(UFT) 엔진 (경로 팩트만)

| 항목 | 경로 | 비고 |
|------|------|------|
| CPU 엔진 | `tools/core/unified_field_theory_engine.py` | import·단위 테스트에서 경로 확인 시 본 행 인용 |
| GPU 변형 | `tools/core/unified_field_theory_engine_gpu.py` | 동일 |

---

**상태**: 초기 SSOT 고정 (2026-03-29). §7 NotebookLM→vault 표·§9 추가 (2026-03-29). §9 작전지휘부·OPS_ONEPAGE 갭·§10 UFT 경로 (2026-03-29). §3.1 16-상태 실험 JSONL·경로 팩트 (2026-03-29). **§4 평행 코퍼스 격벽 정책** (2026-03-30). `tests/multi_corpus_policy.py`·격벽 테스트 (2026-03-30). **§2.1 dual-regime 하이브리드·16상 미연동 팩트** (2026-03-30). **§1.1 Multi-Lens·TOE 비단정** (2026-03-30). **§4.5 CROSS_REF 데이터 계약·Prior 비고정** (2026-03-30). `CROSS_REF_DSS_TO_STATES_DRAFT.json` v2·테스트 정합 (2026-03-30). `CROSS_REF_DRAFT_V2_DOCUMENT.schema.json`·jsonschema 검증 (2026-03-30). CROSS_REF `canonical_ref` ↔ `LOGOS_STATE_MAPPING_V1` 정합 (2026-03-30). ENTRY_06 DSS 페셔·`run_prophecy_alignment_pytest.ps1` 워크스페이스 Fact-Lock (2026-03-30). **CROSS_REF 초안 16행** (LOGOS `state_id` 1–16 전수·ENTRY_11 `analogy_bench`·ENTRY_12–16 DSS 보강)·`link_type`(thematic/temporal/analogy_bench/lexical) 분류·`P0_COMMERCIALIZATION_TRACKER` Step4 직렬 게이트 (2026-03-30). 경로가 바뀌면 본 파일을 먼저 수정한다. **§4.5** `note` 행·스키마 선택 필드·ENTRY_11 NL v2.1 반증 박제 (2026-03-30). **`SASANG_CROSS_REF_DRAFT.json`**·`test_sasang_cross_ref_draft.py`·`run_prophecy_alignment_pytest` 번들·CI 단계 (2026-03-30). **§3.3** `MYEONGRI_INSIGHT_SSOT.md`·관측 JSONL·`MYEONGNI_FUSION_INTERFACE_STUB.json`·`test_myeongni_insight_observation_log.py` (2026-03-30). **§4.6** `MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md`·`run_prophecy_alignment_pytest` 번들에 명리 통찰 테스트 포함 (2026-03-30). **ENTRY_16 소스 헌트 로그/요약/승격 게이트 계약 아티팩트·테스트·CI 번들 편입** (`docs/final/artifacts/entry16_source_hunt_log.jsonl`, `docs/final/artifacts/entry16_source_hunt_summary.json`, `docs/final/artifacts/entry16_promotion_gate.json`, `tests/test_entry16_source_hunt_log.py`, `tests/test_entry16_source_hunt_summary.py`, `tests/test_entry16_promotion_gate.py`, 로컬/CI 번들) (2026-03-30).
