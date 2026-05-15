# Logos 딥 리서치 — Track B 백로그 v1

**schema:** `logos_deep_research_track_b_backlog_v1`  
**last_updated_utc:** 2026-05-02  
**Fact-Lock:** 구현 범위·경로는 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 및 호출 가능 스크립트·exit code로만 확정한다.

**조감도(레이어 맵):** `docs/final/LOGOS_SYMBOLIC_INTERPRETATION_LAYER_MAP_V1.md` — L0–L10 배관·격벽·대외 추출구 한 화면 SSOT.

---

## 지휘관 전용 심층 리포트 — 핵심 축 (Track B)

**SSOT:** `docs/final/artifacts/LOGOS_DEEP_RESEARCH_COMMANDER_REPORT_AXES_V1.json`

보고서 상단에 반드시: **`[TRACK B / HYPO]`**, **`[연구용: 최종 판단은 지휘관 대기]`**. Track A(방패)는 증류 JSON·기존 렌즈 산출만 소비; Track B(망원경)는 장문·다단계 추론을 허용하되 **채택·폐기는 지휘관**.

| 순위 | 축 | 지휘관이 보는 것 |
|------|-----|------------------|
| 1 | 원어·형태·스트롱 앵커 | `verse_id`·`quote_hash`·재현 가능 표면/4D |
| 2 | 교차 참조 그래프 경로 | 노드·엣지 타입·근거 스니펫 연쇄 |
| 3 | 게마트리아·4D 브리지 | [HYPO]·코퍼스 범위·비물리 측정 고지 |
| 4 | 역사·문헌 맥락 | FACT/HYPO 분리·상용 주장 합선 금지 |
| 5 | 통찰 후보·survivor | 허브/군집·임계치·자동 승격 아님 |
| 6 | Track A 증류 연결 | 채택 시에만 `logos_deep_research_distill_v1`·provenance |

배너는 **채택 게이트와 산출물 구분**을 위해 사용한다. 대외 규제·상용 적합성은 **별도 법무·제품 기준** 검토 대상이다.

---

## 목표 (In scope)

- 원어·스트롱·교차참조·(선택) 게마트리아 등 **오프라인** 지식을 **버전드 슬라이스**로 인제스트한다.
- 무거운 탐색·RAG·그래프 순회는 **Track B / 배치**에서만 수행한다.
- 산출은 **`logos_deep_research_distill_v1`** 스키마로 **증류**(결정론적 필드 + 검증 가능한 `evidence_refs`)하여 디스크에 고정한다.
- 본선·실시간 조율자는 **증류 JSON 또는 기존 `run_lens_logos.py` 가벼운 산출**만 소비한다.

## 비목표 (Out of scope)

- A-track·실매매·임상 운영 게이트의 **실시간** 경로에 300만 단계 탐색·대형 LLM 컨텍스트를 직접 연결한다.
- 성경(Logos) 단독으로 **주문·사이징 트리거**를 확정한다. (`non_gating_ack` 유지)
- NotebookLM·브리핑만으로 “구현 완료”를 단정한다.

## 슬라이스 (우선순위)

1. **슬라이스 0 — 계약 고정:** `LOGOS_DEEP_RESEARCH_DISTILL_CONTRACT_V1.json` · `logos_deep_research_distill_v1.schema.json` · 드라이런 `run_lens_logos_deep_fusion.py`.
2. **슬라이스 1 — 코어 구절 파이프라인 정렬:** `scripts/build_logos_corpus_manifest_v1.py` → `docs/final/artifacts/logos_corpus_manifest_v1_latest.json` (계약 `LOGOS_CORPUS_MANIFEST_V1_CONTRACT.json`, 스키마 `logos_corpus_manifest_v1.schema.json`, 회귀 `tests/test_logos_corpus_manifest_v1.py`). 기본 입력 `data/logos/verse_4pipeline_full_31102.json` — 행 수·SHA-256·중복·샘플 `verse_id`.
3. **슬라이스 2 — 매니페스트·그래프 번들:** `scripts/build_logos_corpus_graph_bundle_v1.py` → `docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json` (계약 `LOGOS_CORPUS_GRAPH_BUNDLE_V1_CONTRACT.json`, 스키마 `logos_corpus_graph_bundle_v1.schema.json`, 회귀 `tests/test_logos_corpus_graph_bundle_v1.py`). 코퍼스 매니페스트 + `bible_meaning_graph_*` JSONL 해시·행 수·엣지 타입 분포·구절 ref 교집합; 그래프 원본은 읽기 전용.
4. **슬라이스 3 — 벡터 인덱스 정책(스텁):** `docs/final/artifacts/LOGOS_VECTOR_INDEX_POLICY_V1.json` + 스키마 `logos_vector_index_policy_v1.schema.json` + 계약 `LOGOS_VECTOR_INDEX_POLICY_V1_CONTRACT.json`; 준비 게이트 `scripts/run_logos_vector_index_stub_v1.py` (`--dry-run`·선택 `--require-bundle`). 실제 임베딩·ANN 빌드는 정책의 `status`가 `active`로 승격된 뒤 별도 작업.
5. **슬라이스 4 — 정책 체인 준비도(결정론 게이트):** `scripts/report_logos_track_b_policy_readiness_v1.py` → `docs/final/artifacts/logos_track_b_policy_readiness_v1_latest.json` (계약 `LOGOS_TRACK_B_POLICY_READINESS_V1_CONTRACT.json`, 스키마 `logos_track_b_policy_readiness_v1.schema.json`, 회귀 `tests/test_logos_track_b_policy_readiness_v1.py`). 신학 베이스라인·provenance 경로·증류 계약/스키마 일괄 확인·exit code; LLM 없음.
6. **슬라이스 5 — 오프라인 딥 퓨전 잡(스켈레톤):** `scripts/run_logos_track_b_deep_fusion_job_v1.py` → `docs/final/artifacts/logos_track_b_deep_fusion_job_v1_latest.json` (계약 `LOGOS_TRACK_B_DEEP_FUSION_JOB_V1_CONTRACT.json`, 스키마 `logos_track_b_deep_fusion_job_v1.schema.json`, 회귀 `tests/test_logos_track_b_deep_fusion_job_v1.py`). 기본 `logos_track_b_policy_readiness_v1_latest.json`의 `overall_ok` 게이트(`--skip-readiness-check`는 로컬만); **기본 LLM/RAG 미호출**·플래그 예약; 향후 증류·RAG는 별도 모듈.

## 산출 스키마 (증류)

- **SSOT:** `docs/final/schemas/logos_deep_research_distill_v1.schema.json`
- **메타 계약:** `docs/final/artifacts/LOGOS_DEEP_RESEARCH_DISTILL_CONTRACT_V1.json`
- **기본 산출 경로(향후):** `docs/final/artifacts/logos_deep_research_distill_latest.json`

필수 의미: `state_vector_logos.mean_4d`, `epistemic_uncertainty`, `veto_flags`, `evidence_refs[]`(verse_id·quote_hash), `non_gating_ack`, `provenance`.

## 게이트 (Track B)

- 인제스트 빌드: 행 수·NULL 비율·중복 키·매니페스트 SHA-256 기록.
- 증류 빌드: JSON Schema 검증 통과·`hypothesis_tier=B`·`boundary_ack=true`.
- 실패 시: A-track로 아무 것도 승격하지 않음; `veto_flags.insufficient_evidence=true` 등으로 소비측에서 가중 제거만 허용.

## 금지 사항

- 융합 스텁(`report_independent_lens_fusion_stub_v0.py`)·실시간 조율자에 **미증류 원시 그래프** 직접 연결.
- `research_only`·B-track 산출을 상용 주장·실거래 근거와 **문장 합선**.

## 참조

- 로고스 독립 렌즈 v0: `LOGOS_INDEPENDENT_LENS_V0_CONTRACT.json`, `scripts/run_lens_logos.py`
- 융합 스텁 v0: `INDEPENDENT_LENS_FUSION_STUB_V0_CONTRACT.json`
- MKM 신학 베이스라인(파라미터 해석 정책): `LOGOS_MKM_THEOLOGY_BASELINE_V1.json` · 계약 `LOGOS_MKM_THEOLOGY_BASELINE_V1_CONTRACT.json`
- 정책 체인 준비도: `logos_track_b_policy_readiness_v1_latest.json` · `LOGOS_TRACK_B_POLICY_READINESS_V1_CONTRACT.json`
- 딥 퓨전 잡(스켈레톤): `logos_track_b_deep_fusion_job_v1_latest.json` · `LOGOS_TRACK_B_DEEP_FUSION_JOB_V1_CONTRACT.json`
- 중앙 메모리: `docs/final/CENTRAL_AGENT_MEMORY_V1.md` (Multi-Lens·Fact-Lock)
