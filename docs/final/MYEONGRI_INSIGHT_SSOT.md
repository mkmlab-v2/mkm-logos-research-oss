# 명리 통찰 작업 SSOT (B-track)

**작성일**: 2026-03-30  
**목적**: 다중렌즈 **융합 중간레이어**는 별 채팅/SSOT에서 다루고, 본 문서는 **명리 통찰·반증·관측 기록**만 순서대로 고정한다.  
**상위 팩트**: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` (명리 분리·Promotion Loop·CROSS_REF 격벽).

---

## 0. 전제 (역할·금지선)

| 항목 | 내용 |
|------|------|
| **이 스트림의 역할** | 명리 **입력 정의**, 통찰·가설, **반증**, 원장/아티팩트 박제. |
| **다른 스트림** | 다중렌즈 융합 엔진·중간레이어 구현은 **중복 설계하지 않음**; 인터페이스만 §6 참조. |
| **금지** | A-track 정경·실매매·OOF·레짐 캡에 **자동 합선**; `[HYPO]`·B-track 밖으로 단정 승격 금지. |
| **출력 단위** | 매 회: 가설 한 줄 + 근거 유형 + **다음 검증 한 가지**. |

---

## 1. 입력·용어 SSOT

### 1.1 식별자 층 (택일 후 일관 유지)

| 층 | 용도 | 저장소 참조 |
|----|------|-------------|
| **`state_id` 1–16** | 16상 슬롯·벤치·로고스 스냅샷 조인 | `data/myeongni/16_STATE_MASTER_PROBE_v1.json`, `docs/final/artifacts/LOGOS_STATE_MAPPING_V1.json` |
| **간지·오행 문자열** | L₃·갑자 매핑·서술 | `Gapja4DVectorMapper` 등 `tools/prophecy`·`tools/core` (호출 시점에만 인용) |
| **절기·대운·세운** | 숫자 주기 벤치(364↔대운 등) | **데이터 테이블 SSOT 지휘관 확정 전**에는 `[HYPO]` 또는 “정의 후 벤치”로만 기록. |

### 1.2 시간 뼈대 (고정 규칙)

- **양력/음력/절기** 중 무엇을 “사건 시점”으로 쓸지 **한 세트로 고정**하고, 바꿀 때는 `run_id` 또는 날짜 범위를 새로 잡는다.

| 자원 | SSOT 경로 (확정 시 기입) | 비고 |
|------|---------------------------|------|
| 대운·세운 수치 테이블 | `docs/final/artifacts/myeongri_daewoon_sewoon_table_registry_v1.json` | 경로 락(고정): 테이블 미확정 상태도 반드시 이 레지스트리에 기록하고, 추정 경로·임시 로컬 파일을 SSOT로 사용하지 않는다. |

---

## 2. 관측 로그 (주간 누적)

- **파일**: `data/myeongni/insight_observation_log.jsonl` (부트스트랩 4행·회귀용; 주간 append).
- **샘플 형식**: `data/myeongni/insight_observation_log.sample.jsonl` (동일 계약).
- **검증**: `tests/test_myeongni_insight_observation_log.py`.
- **필수 필드 의미**: `ts_utc`, `inputs_summary`, `insight_one_liner`, `falsification_hook`, `hypothesis_tier`=`B`, `boundary_ack`=`true`.

---

## 3. 반증·오염 체크 (통찰마다)

- [ ] **맥락 오염**: 연대기/행정 텍스트에 묵시·상전이를 **동치**로 붙이지 않았는가.
- [ ] **False equivalence**: 서로 다른 전통·도메인을 **같은 존재론**으로 합치지 않았는가.
- [ ] **숫자 은유**: 364일·대운 등 **정의 없는 숫자만** 대조하지 않았는가.

---

## 4. 아티팩트 박제

- CROSS_REF 행의 **`note`** 블록: NL 요약·반증 유형·`[HYPO]` 승격 보류·A-track 합선 금지 — `docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json` `ENTRY_11` 패턴 재사용.
- 스냅샷 조인 시 `canonical_join_ssot` / `LOGOS_STATE_MAPPING_V1` 버전을 한 줄 명시.

---

## 5. 도메인 분기

| 트랙 | 내용 |
|------|------|
| **건강·처방** | `integrated_prescription_engine`·코호트: `KOREAN_MEDICAL_CANON_INGEST_HANDOFF`·A/B 격벽 후 깊게. |
| **자산·레짐** | 얇은 하네스(갑자 on/off·레짐 라벨만)만; PnL·캡은 Promotion 프로토콜 이후. |

---

## 6. 융합 스트림과 인터페이스 (단일 SSOT)

**기계-readable 스텁**: `docs/final/MYEONGNI_FUSION_INTERFACE_STUB.json` (`schema: myeongni_fusion_interface_stub_v1`).

명리 측이 **넘길 수 있는 것**:

- `myeongri_gapja` (2글자 갑자, L₃ 입력용)
- `state_id` 또는 실험 `experiment_id` / `run_id`
- 짧은 `rationale` 문자열 (비트리거)

융합 측이 **요구 시 명시할 것**: 가중·렌즈 활성 조건·버전 문자열.

---

## 7. 완료 정의 (이 스트림)

| 단계 | 최소 완료 | 강화 완료 |
|------|-----------|-----------|
| 초기 | §1 시간 규칙 1줄 + 샘플 로그 4행 | + CROSS_REF식 `note` 1건 |
| 운영 | 4주 원장 + 반증 체크 3건 통과 | + 융합 인터페이스 합의 10줄 |

---

## 8. 고급·대면 답변 규격 (MKM 명리 v1, 권장)

**상위 정렬**: `docs/final/CENTRAL_AGENT_MEMORY_V1.md` 「명리 렌즈 고도화 v1」— **결정론 JSON·스키마가 사실 층**, NL은 번역·가설 층.

| 단계 | 필수 내용 | 비고 |
|------|-----------|------|
| **A. 입력 고지** | `birth_instant_utc` + IANA TZ(또는 동일 계약), `as_of_utc` | DST·모호 시 **보간 금지**·누락 시 `missing_input` |
| **B. 결정론 앵커** | `myeongri_complete_fusion` / `myeongni_independent_lens_v1` / `myeongni_core_vector_v1` / `daewoon_timeline_v1` 등 **레포 스크립트 산출 필드 인용**(경로·해시·발췌) | 숫자·간지·대운은 **파이프라인 밖 상식으로 보정 금지** |
| **C. 렌즈 서술** | **중기 방향·구조·타이밍**만; 실매매·임상·단일 운명·교리 최종 판정 **금지** | `[HYPO]` 기본 |
| **D. 멀티렌즈 순서** | `Field` → `Lens(사상/명리/성경)` → `Conflict` → `Final Action` 요약 한 블록 | 성경·로고스는 `[NON_GATING]` |
| **E. LLM 봉투** | 고객·카피용 자연어는 `MYEONGRI_AI_INTERPRETATION_PROMPT_TEMPLATE_V1.md` + `schemas/myeongri_ai_interpretation_envelope_v1.schema.json` 준수; `rag_sources_used`에 실제 주입 경로 기록 | `human_review_required=true` 유지 |

**한 페이지 체크**: 호출 전 `MYEONGRI_AI_INTERPRETATION_PROMPT_TEMPLATE_V1.md` §5 운영 체크리스트.

---

## 9. Vault / F: 참고 원천 색인 (B-track, RAG·NotebookLM 보강용)

**Fact-Lock**: 아래 경로는 **브리핑·RAG 후보**이며, 구현·OOF·트리거 판정은 여전히 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`·`exit code`·아티팩트만 SSOT다. 학술지 형태의 “명리 단행 논문”은 희소하고, 실측 스캔(2026-05) 기준 **대부분이 MKM·NotebookLM 미러 MD·내부 설계**다. 외부 업계 패턴 요약은 `docs/final/AI_MYEONGNI_MANSE_EXTERNAL_REFERENCE_LANDSCAPE_2026-03-29.md`를 우선한다.

| 구분 | 대표 경로 (로컬·Vault) | 용도 |
|------|-------------------------|------|
| **레포 SSOT** | `MYEONGRI_EXTERNAL_ENGINEERING_LEXICON_V1.md`, `MYEONGRI_AI_INTERPRETATION_PROMPT_TEMPLATE_V1.md`, `schemas/myeongri_ai_interpretation_envelope_v1.schema.json` | 규격·대외 어휘·봉투 |
| **G: NotebookLM 미러** | `G:\공유 드라이브\MKM_DATA_VAULT\notebooklm_sources\일반예언\명리_오행_십성_4D_수학적_매핑_규칙_코드기준_2026-03-14.md` | 4D 매핑·코드 기준 서술 |
| **G: NotebookLM 미러** | 동 폴더 `명리_대운_세운_4D_경로_설계안_2026-03-14.md`, `만세력_명리_우리이론_통합_업그레이드_분석_2026-01-06.md` | 대운·세운·통합 설계 맥락 |
| **G: 제품/연구 묶음** | `...\notebooklm_sources\만세력_사주_AI_A_제품\`, `...\만세력_사주_AI_B_연구\` 내 `MYEONGNI_FUSION_DECISION_JSON_SCHEMA_2026-03-29.md`, `MYEONGNI_FUSION_MAPPING_PROXY_2026-03-29.md` | 융합 JSON·프록시 초안 |
| **G: Vault 미러** | `G:\공유 드라이브\MKM_DATA_VAULT\vault\notebooklm_sources\docs\final\AI_MYEONGNI_MANSE_EXTERNAL_REFERENCE_LANDSCAPE_2026-03-29.md` | 외부 제품 패턴 (B-only) |
| **F: 아카이브** | `F:\BACKUP\MKM_ARCHIVE_FROM_F\workspace_archive\mkm_vertex_ai_archive\...\MKM12_명리_브릿지_성경_검색_융합_완료_2026-01-07.txt` 등 | 역사적 브리지·통찰 원문 (검증 후 인용) |
| **정규화 카탈로그** | `docs/final/artifacts/myeongri_external_reference_catalog_latest.json` + 스키마 `docs/final/schemas/myeongri_external_reference_catalog_v1.schema.json` | 외부 참고문헌 등급(A/B/C)·태그·권장용도 SSOT |

**동기화**: Vault 상단은 `scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1`로 갱신 가능; RAG에 넣을 때는 `rag_sources_used`에 **실제 파일 경로**를 박는다.
**추천 자동화**: `py scripts/recommend_myeongri_external_references_v1.py --profile daewoon --top-n 5` 로 질문 유형별 `rag_sources_used_suggested`를 생성해 봉투에 그대로 주입한다.
**원클릭 조립**: `py scripts/build_myeongri_ai_prompt_with_refs_v1.py --profile daewoon --deterministic-json <path> --recommendation-out docs/final/artifacts/myeongri_external_reference_recommendation_latest.json` 으로 추천+프롬프트를 한 번에 생성한다.
**종단 체인**: `py scripts/run_myeongri_ai_prompt_chain_v1.py --profile daewoon --prompt-out docs/final/artifacts/myeongri_ai_prompt_latest.txt --deterministic-json <path>` 후, 응답 파일이 생기면 `--response-file <llm_response.txt> --validated-envelope-out docs/final/artifacts/myeongri_ai_envelope_validated_latest.json`로 스키마 검증까지 연결한다.
**일일 자동(옵셔널)**: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-MyeongriAiPromptChainDailyTask.ps1 -DailyAt 10:40` (충돌 완화 기본시각). 해제는 `-Remove`, 점검은 `-WhatIf`.
**답변 템플릿 팩(ko/en)**: `py scripts/build_myeongri_answer_template_pack_v1.py` → `docs/final/artifacts/myeongri_answer_template_pack_latest.json` (profile별 표준 문안 뼈대).
**답변 초안 자동생성**: `py scripts/build_myeongri_answer_draft_v1.py --profile daewoon --lang ko` → `docs/final/artifacts/myeongri_answer_draft_latest.json` + `.md` 생성. 일일 체인에서는 `Run-MyeongriAiPromptChainDaily_v1.ps1 -BuildAnswerDraft` 또는 등록 스크립트 `-BuildAnswerDraft`로 연결.

---

**상태**: 순서 0→2 부트스트랩·§6 스텁·JSONL 회귀 테스트 추가; §1.2 경로는 `myeongri_daewoon_sewoon_table_registry_v1.json`으로 고정(테이블 값은 레지스트리 상태값으로 관리). 2026-04-16 기준 상용 게이트 기본 입력은 `docs/final/artifacts/kospi_myeongri_wf_gates_v4_1_latest.json`(label rule `+1.0/-1.0`)로 운영 고정.

---

## 문서 라벨 규칙 (Fact-Safe)

| 라벨 | 의미 | 사용 기준 |
|------|------|-----------|
| `[FACT]` | 재현·추적 가능한 진술 | 본 문서의 경로·스키마·`pytest`·상위 `CONSTITUTION` 팩트와 일치; 관측 로그 계약 필드는 스텁·샘플로 고정 검증 |
| `[HYPO]` | 명리 통찰·가설·미확정 입력 | `insight_one_liner`, `hypothesis_tier=B`, 표의 `—`·지휘관 미확정 칸; 승격·A-track 합선 전까지 단정 금지 |
| `[VISION]` | 융합·Promotion·로드맵 | 섹션 6 인터페이스 합의, 섹션 5 트랙 분기의 **상용·심화** 쪽; 목표이지 본선 단정 아님 |
| `[NON-MEDICAL]` | 비의료 고지 | 명리·시간 주기 해석은 **의료 진단·치료·효능 주장 아님**; 건강·처방 트랙은 별도 핸드오프·격벽 문서를 따름 |

스트림 0→7: 매 회 출력(가설 한 줄·반증 훅)은 기본적으로 `[HYPO]`로 취급하고, 로그 파일·테스트·버전 문자열이 붙은 운영 규칙만 `[FACT]`에 해당한다.
