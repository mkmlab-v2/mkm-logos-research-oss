# 내부 전용 — 시맨틱 · RAG · 4D 보정 3단 아키텍처 설계도 (목차 SSOT v0.2)

**분류:** 내부 엔지니어링 메모 · **B-track·연구·품질 설계** — 대외 제안서·상용 주장·임상·실매매 트리거와 **합선 금지**.  
**목적:** “의도 → 근거 → 맥락 보정” 파이프라인을 **동일 어휘**로 고정하고, 구현·평가·로그를 맞출 **목차·체크리스트**를 제공한다.  
**Fact-Lock:** 구현·경로 확정은 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 및 호출 가능 스크립트가 우선. 본 문서는 **설계 방향**만 고정한다.

**연계:** 출원 전 1p 요약 준비 `docs/final/B2G_TECH_DISCLOSURE_ONEPAGER_PREP_V1.md` · 제안 복붙 부록 `docs/final/B2G_CONTROL_INTEGRITY_PROPOSAL_ANNEX_V1.md` — 역할이 다르며 본문 **이중 기술 금지**.

**문서 버전:** v0.2.2 · **갱신:** 2026-05-14 — Premium multi-lens 리포트 → 번들 `--premium-multilens-report-json`·병합 순서·CONSTITUTION 갱신

---

## 1. 문서 범위 (DoD)

- [x] **4D** 라벨 분리 표(2.1) 및 용어 표(2) 초안 확정 — 팀 리뷰 시 수정 가능
- [x] **번역 브리지** 출력 계약: `docs/final/schemas/semantic_rag_bridge_insight_bundle_v1.schema.json` + 예시 + `tests/test_semantic_rag_bridge_insight_bundle_schema_v1.py`
- [x] **데이터 플로우** 각 박스가 구현 스크립트와 **전부** 매핑(**§4.1** 표; Premium → `rag_evidence`: **`--premium-multilens-report-json`**)
- [x] **베이스라인 대비 지표** 오프라인 1회 수치 기록 (6절 **A-pilot** 행; RAG 미연결 비율 본측정은 후속)

---

## 2. 용어 사전 (동명이의 금지)

| 레이블 | 이 설계도에서의 의미 | 레포에서 흔한 다른 의미(혼동 금지) |
|--------|----------------------|-------------------------------------|
| **시맨틱(의도)** | 질의·세션·도메인 컨텍스트를 **검색 쿼리·라우터 입력**으로 바꾸는 층(임베딩 검색, 키워드 확장, 렌즈 라우팅 등) | “LLM이 알아서 이해”만을 지칭하지 않음 |
| **RAG** | **승인된 코퍼스**에서 청크를 가져와 생성·판단에 **근거로 붙이는** 층 | NotebookLM UI·MCP만을 지칭하지 않음 |
| **4D 보정** | **구조화된 상태 벡터·메타데이터**를 프롬프트·정책·게이트에 주입해 톤·경로·위험도를 조정하는 층 | (1) 명리 `vector_4d` 계열 (2) `logos_4d_state_v1`(거시 입력 기반 좌표) (3) 압축 시드 S,L,K,M (4) Prism 분류 라벨 — **동일 호출명 금지** |
| **번역 브리지** | 수치·그래프·엣지 결과를 **스키마화된 JSON·짧은 자연어 슬롯**으로 변환하는 전용 모듈 | LLM에게 원시 로그를 통째로 넣는 것과 구분 |

### 2.1 「4D」레포 고정명 분리 (혼동 시 설계 오류)

| 고정명 | 의미(한 줄) | 대표 산출·스크립트(예) | 본 3단 설계에서의 역할 |
|--------|-------------|------------------------|-------------------------|
| **명리 `vector_4d` 계열** | 만세력·지장간·학파 블렌드 등 **명리 렌즈 수치 벡터** | `scripts/myeongri_complete_fusion.py`, `rule_school_mkm_4d_v1` | 보정층: **개인·시점** 기반 calibration |
| **`logos_4d_state_v1`** | 출애굽·거시 스모크에서 온 **좌표·사분면**(스키마명 4D, 실질 2축+X) | `scripts/build_logos_4d_state_v1.py` → `logos_4d_state_v1_latest.json` | 보정층: **거시 내러티브** advisory, 원어 게마트리아와 무관 |
| **압축 시드 S,L,K,M** | Track A/B 압축 파이프라인 **시드 축** | `CONSTITUTION` 헤더·압축 러너 | **코드 4D 벡터**; Prism·명리 벡터와 **혼동 금지** |
| **Prism S/L/K/M** | Grand Indexing **파일·경로 분류 라벨** | `MKM12_PRISM_INDEX_REGISTRY_V1.json` | 인덱스·온보딩; **역학 수치 아님** |
| **렌즈 뮤직 `gematria_seed_trace`** | 상징→오디오 B-track **감사 꼬리표** | `run_lens_music_gematria_gate_chain_v1.py` 등 | **사상·심볼 레인**; Logos 본문 해석 엔진 아님 |
| **`vector_4d` in Logos batch** | `run_lens_logos.py` 배치 JSON에 실린 **절별 수치 필드** | `data/logos/4lens_batch_sample.json` 등 | 렌즈 배치 입력; 일일 `logos_4d_state`와 **동명이의 별개** |

---

## 3. 아키텍처 한 장 (논리)

```
[사용자/배치 입력]
       ↓
[1 시맨틱·라우팅]  ←── 도메인·렌즈·의도 확정, 쿼리 정규화
       ↓
[2 RAG 검색·재순위] ←── 코퍼스 청크, 인용 후보, 라이선스 메타
       ↓
[번역 브리지]      ←── 규칙·테이블·스키마로 JSON 슬롯화 (LLM 전)
       ↓
[3 4D·상태 보정]   ←── (도메인별) 벡터·밴드·게이트 입력
       ↓
[생성/오케스트레이션] ←── LLM 또는 템플릿 슬롯 채움
       ↓
[통제·감사]       ←── HOLD, exit code, JSONL·구조화 로그
```

---

## 4. 데이터 플로우 & 계약 (초안 표)

| 단계 | 입력(예) | 출력(예) 스키마/파일 자리 | 레포 앵커(예시, 전부 아님) |
|------|----------|---------------------------|---------------------------|
| 시맨틱 | raw query, session meta | `query_plan_v1`, `lens_route` | 렌즈 라우팅·파일럿: CONSTITUTION 표 `philosophy_lane_rag_pilot_v1` 등 |
| RAG | query_plan, corpus_id | `retrieval_runs[]`, `hits[]` | `build_premium_btrack_multilens_report_v1.py` 오프라인 RAG, 기타 `build_cross_lens_rag_fusion_v1.py` |
| 번역 브리지 | hits + 도메인 규칙 + calibration 포인터 | **`semantic_rag_bridge_insight_bundle_v1`** | 스키마·예시 `docs/final/schemas/` · 빌더 **`scripts/build_semantic_rag_bridge_insight_bundle_v1.py`** (`--rag-json`, `--premium-multilens-report-json`, `--philosophy-pilot-json`) → `docs/final/artifacts/semantic_rag_bridge_insight_bundle_v1_latest.json` |
| 4D 보정 | `calibration_reference.kind`에 맞는 스냅샷 | 동 번들 내 `calibration_reference` + 후속 `calibration_overlay` | 2.1 표 참조; 명리·`logos_4d_state_v1`·시장 사상 스냅샷 등 |
| 통제 | 위 산출물 | exit code, `audit.jsonl` | `athena_run_v1.py`·CONSTITUTION §28 요지 |

**번역 브리지 계약 요약:** `rag_evidence[]` + `structured_insight_slots[]` + `calibration_reference` + `policy`(track/gating). LLM에는 **이 번들만** 주입하는 것을 목표로 한다.

### 4.1 파이프라인 박스 ↔ 스크립트 매핑 (Fact-Lock 앵커)

| 논리 박스 (§3) | 주요 스크립트·산출 | 비고 |
|----------------|-------------------|------|
| 사용자/배치 입력 | 각 도메인 CLI·HTTP 라우트 | 예: `philosophy_lane_rag_pilot_v1.py --user-query …`, `build_premium_btrack_multilens_report_v1.py` 플래그 |
| 1 시맨틱·라우팅 | `scripts/philosophy_lane_rag_pilot_v1.py` → `docs/final/artifacts/philosophy_lane_rag_pilot_v1_latest.json`; `scripts/run_graphrag_pilot_router_v1.py`; Premium 리포트 내 질의·렌즈 메타(`build_premium_btrack_multilens_report_v1.py`) | 금지어·메뉴 ID·ANN 스킵 사유는 파일럿 JSON |
| 2 RAG 검색·재순위 | `scripts/query_logos_vector_index_ann_lite_v1.py`(파일럿 상류); `scripts/build_premium_btrack_multilens_report_v1.py`(오프라인 RAG 번들); `scripts/build_cross_lens_rag_fusion_v1.py` → `docs/final/artifacts/cross_lens_rag_fusion_latest.json` | hits 스키마는 경로별 상이; 번들 `--rag-json`은 호출측 정규화 |
| 번역 브리지 | `scripts/build_semantic_rag_bridge_insight_bundle_v1.py`(`--rag-json`, **`--premium-multilens-report-json`**, **`--philosophy-pilot-json`**; 병합 순서 고정) → `docs/final/artifacts/semantic_rag_bridge_insight_bundle_v1_latest.json` | `semantic_rag_bridge_insight_bundle_v1`; 회귀 pytest |
| 3 4D·상태 보정 | `scripts/build_logos_4d_state_v1.py`; `scripts/myeongri_complete_fusion.py`; `scripts/run_market_sasang_lens_v1.py`; `scripts/run_market_myeongni_lens_v1.py`; 압축·Prism은 CONSTITUTION 표·`scripts/run_ultra_compression_default.py` 등 | `calibration_reference.kind`로 단일 4D 패밀리만 표기 |
| 생성/오케스트레이션 | `scripts/athena_run_v1.py` 래핑·수동 LLM; `projects/mkm/mkm-life/.../philosophy/rag-pilot/route.ts` | 본 설계도 범위 밖 다수 |
| 통제·감사 | `scripts/athena_run_v1.py`; `scripts/log_agent_decision.py` → `reports/agent_decisions_log.jsonl` | CONSTITUTION 실행 거버넌스 절 |

**원클릭(로컬, 선택):** Premium 예시 또는 실제 리포트 JSON이 있을 때  
`py scripts/build_semantic_rag_bridge_insight_bundle_v1.py --calibration-kind logos_4d_state_v1 --calibration-artifact docs/final/artifacts/logos_4d_state_v1_latest.json --premium-multilens-report-json docs/final/schemas/premium_btrack_multilens_report_v1.example.json --philosophy-pilot-json docs/final/artifacts/philosophy_lane_rag_pilot_v1_latest.json --strict`  
(후자·캘리브레이션 파일 없으면 해당 인자 생략 또는 `--calibration-kind none`.)

---

## 5. 단계별 설계 체크리스트

### 5.1 시맨틱·라우팅

- [ ] 질의가 **어느 렌즈·어느 코퍼스**로 가는지 결정 규칙이 문서화되어 있다.
- [ ] **금지 도메인·금지 출력**이 라우팅 단계에서 한 번 걸린다.
- [ ] 시맨틱만 있고 RAG가 없을 때의 **거절·축소 경로**가 정의된다.

### 5.2 RAG

- [ ] 코퍼스 **버전·시행일·출처** 필드가 청크에 붙는다.
- [ ] 재순위 파이프라인(키워드 / 하이브리드 / reranker)이 **스위치 가능**하다.
- [ ] 근거 없는 문장에 대한 **HOLD·재질의** 조건이 정의된다.

### 5.3 번역 브리지

- [ ] LLM 입력은 **원시 그래프 전체가 아니라** JSON 슬롯만 받는다.
- [ ] 슬롯 스키마에 **최대 길이·필수 키·금지 키**가 있다.
- [ ] 브리지 실패 시 **스킵 vs 전체 HOLD** 정책이 있다.

### 5.4 4D·상태 보정

- [ ] 사용 중인 4D 정의가 **표 2장 “4D 보정”** 중 하나로만 고정된다(혼합 시 별도 이름 부여).
- [ ] 보정이 **비차단(advisory)** 인지 **차단(gating)** 인지 렌즈·도메인별로 표에 적는다.
- [ ] “시장·의료·교리” 등 **금지 합선** 문구가 코멘트로 박혀 있다.

### 5.5 통제·감사

- [ ] 성공·실패가 **exit code·JSON 필드**로 남는다.
- [ ] 재현을 위해 **시드·코퍼스 버전·모델 태그**가 로그에 포함된다.

---

## 6. 베이스라인·KPI (내부)

| 구분 | 지표(예) | 비고 |
|------|-----------|------|
| A | 근거 청크 미연결 단정 비율 | RAG 게이트 |
| A-pilot (2026-05-14) | 스키마·빌더 검증 통과율 (로컬) | 1.0 — `py -m pytest tests/test_semantic_rag_bridge_insight_bundle_schema_v1.py tests/test_build_semantic_rag_bridge_insight_bundle_v1.py -q` exit 0 |
| B | 인용 위반·금지어 히트 | 정책·validator |
| C | 톤·분류 일치율(소형 분류기 또는 human spot) | 4D 보정 전후 |
| D | 지연·토큰·비용 | 운영 |

**원칙:** “체감 좋음”이 아니라 **위 표 중 최소 1개**는 숫자로 남긴다.

---

## 7. 실패 모드 매트릭스

| 실패 | 증상 | 로그에서 볼 필드 | 1차 완화 |
|------|------|-------------------|----------|
| 시맨틱 과확장 | 엉뚱한 코퍼스로 라우팅 | `lens_route`, `route_confidence` | 기본 코퍼스·HOLD |
| RAG 노이즈 | 엉뚱한 청크 상위 | `hit scores`, `source_id` | rerank·narrow filter |
| 브리지 왜곡 | JSON 스키마 깨짐 | `bridge_validation_errors` | 스키마 검증·재시도 |
| 4D 오적용 | 톤·정책 충돌 | `calibration_source`, `band` | advisory만 허용 |
| LLM 환각 | 근거 없는 확장 | `citations_missing` | 출력 템플릿·HOLD |

---

## 8. 적응기(LoRA·어댑터·프롬프트 정책) 위치

- **베이스 모델:** 교체 가능한 **하드웨어/게임기** 층으로 둔다.
- **공통 IP(선호):** RAG 코퍼스·게이트·스키마·감사·번역 브리지 — **모델 비의존**.
- **LoRA 등:** “말투·슬롯 채움·도메인 소량 적응”에 한정하고, **통제 로직을 LoRA 안에 숨기지 않는다**(감사 불가 위험).

---

## 9. 레포 Fact-Lock 포인터 (확장 시 필독)

- `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` — 구현 표·§28 실행 거버넌스
- `docs/final/CENTRAL_AGENT_MEMORY_V1.md` — 렌즈 격벽·NON_GATING
- 오프라인 멀티렌즈 RAG: CONSTITUTION 표 `build_premium_btrack_multilens_report_v1.py` 행
- 철학 파일럿: 동 표 `philosophy_lane_rag_pilot_v1.py` 행
- 번역 브리지 번들 스키마: `docs/final/schemas/semantic_rag_bridge_insight_bundle_v1.schema.json` · 빌더 `scripts/build_semantic_rag_bridge_insight_bundle_v1.py` (내부 v0.2.2 / CONSTITUTION 동명 행; `--premium-multilens-report-json`)

---

## 10. 다음 액션 (우선순위)

1. ~~**4D** 분리 표 확정~~ → v0.2 **2.1** (리뷰만 남음).
2. ~~**번역 브리지** JSON Schema v1~~ → `semantic_rag_bridge_insight_bundle_v1` + pytest.
3. ~~**빌더 CLI**~~ → `rag-json` → **`premium-multilens-report-json`** → `philosophy-pilot-json` (24 cap). CI·일일 체인에 고정 삽입은 후속.
4. ~~**A~D 지표 1회**~~ → 6절 **A-pilot** 완료; RAG 미연결 비율 등 **본측정**은 후속.
5. 대외 문서·제안서에는 **본 파일·스키마 경로 링크 금지**(내부 전용).

---

**면책:** 본 설계도는 법무·규제 적합성·특허성을 판단하지 않는다.
