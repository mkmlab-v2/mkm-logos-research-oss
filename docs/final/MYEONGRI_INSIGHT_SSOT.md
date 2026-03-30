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
- **대운·세운 테이블**의 파일 경로·버전이 정해지면 본 절 표에 **한 줄 추가**한다 (미확정 시 빈칸 유지).

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

**상태**: 순서 0→2 부트스트랩·§6 스텁·JSONL 회귀 테스트 추가; §1.2 대운 테이블 경로는 지휘관 확정 시 본 문서에 추가.
