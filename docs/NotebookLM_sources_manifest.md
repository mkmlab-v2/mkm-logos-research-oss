# NotebookLM 소스 매니페스트 (A/B 이원)

**작성일**: 2026-03-29 · **갱신**: 2026-04-23 (Vault 미러: 원어 특이점 글로스 v3·히브리 오버라이드·`master_codebook_lexicon_v1` **포인터** JSON 추가; 동기화 스크립트 `$SourceFiles` 반영) · 이전 갱신 2026-04-12 (A 표: `MKM_CORE_THEORY_V1` · 압축·복원·예언 **통합 노트** `MKM_CORE_INTELLIGENCE_V1` · `COMPRESSION_EVALUATE_REPORT_DATA_FLOW_V1`·`MKM_LESSONS_LEARNED_V1`·`COMPRESSION_RESTORATION_EVOLUTION_INDEX_V1` · **LOG_METABOLISM 전용** `MKM_LOG_METABOLISM_REFINERY_V1` · **CORE↔Refinery 격벽 포인터** `NOTEBOOKLM_LOG_METABOLISM_CORE_BRIDGE_POINTER_V1.md` · 보조 NotebookLM 앵커 2건 · Vault 미러에 `CURRENT_OPS_SNAPSHOT` 포함)  
**정의**: **A = Fact-Lock(팩트 고정)**, **B = Creative-Lock(통찰·가설)**. B는 본선 OOF·실매매 트리거와 A를 혼선 없이 적용.

**Cursor 3.0 (2026-04)**: NotebookLM과 동일하게 **브리핑·질의·소스 아카이브** 레이어다. **에이전트 병렬(Agents Window)·Design Mode**는 제품 기능이며, **압축 엔진·헌법·실매매 SSOT는 여전히 레포의 `.py`/JSON**이다(`AGENTS.md`, `COMPRESSION_SLA_POLICY_V1.md`).

**연구 서사 인덱스 (B, 비-SSOT):** `docs/final/RESEARCH_HISTORY_V1.md` — MCP `notebook_list`로 수집한 **노트북 제목·ID 스냅샷**(구현·게이트 팩트 아님). 갱신 시 이 파일을 먼저 고친 뒤 Vault 동기화.

**Vault 동기화**: `scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1`가 이 표를 `notebooklm_sources/`로 복사(SSOT 반영). 공유 Vault 루트는 환경의 `MKM_VAULT_ROOT` 또는 스크립트 `-VaultRoot`로 지정.

### Vault 동기화 — 로컬 부재 Skip (정상, 2026-04)

아래 경로는 스크립트의 복사 목록에 있으나 **최소 클론·본 저장소 트리에 없을 수 있다**. 부재 시 동기화는 건너뛰며(스크립트는 해당 7개를 **optional**로 처리해 WARNING 대신 회색 한 줄만 출력), **오류가 아니다**.

| 경로 | 비고 |
|------|------|
| `projects/bitcoin-trading/ops/v2/memory/decision_ledger.py` | 현재 원격 인덱스에 없음 — VPS/별도 배포 트리에 있을 수 있음 |
| `projects/bitcoin-trading/ops/v2/memory/fact_lock_snapshot.py` | 동일 |
| `projects/bitcoin-trading/ops/windows-rehearsal/WAITING_QUEUE_DUAL_BTC_RUNBOOK.md` | 동일 |
| `projects/bitcoin-trading/ops/windows-rehearsal/DAILY_EXECUTION_INSIGHT_BRIEF_TEMPLATE.md` | 동일 |
| `backtest_results/LOGOS_RESONANCE_BTC_BULL_FULL.json` | `backtest_results/`는 `.gitignore` — 로컬 생성·역수입 시에만 존재 |
| `backtest_results/LOGOS_RESONANCE_BTC_BEAR_FULL.json` | 동일 |
| `backtest_results/LOGOS_RESONANCE_BTC_SIDEWAYS_FULL.json` | 동일 |

**권장**: 일상 운영은 부재를 **무시**해도 됨(`copied`만으로 미러 성공 판단). 목록에서 경로를 **삭제(Prune)** 하지 않는 한, 나중에 파일이 생기면 **같은 스크립트가 자동으로 포함**한다.

### Unified-Intelligence — 메인 지휘 (2026-03-29)

- **통합 전황판 (A1 16-State + Logos Phase 1 + Git 슬롯)**: `docs/final/UNIFIED_INTELLIGENCE_BATTLEBOARD_2026-03-29.md`
- **합류 방식**: 병렬 창은 **경로·커밋 해시·exit code**로만 보고 → 메인에서 매니페스트·전황판 갱신. **매니페스트 직접 편집은 메인 창만.**

### Gemini ↔ NotebookLM — 작전 브리핑 앵커 (2026-04)

**목적**: 지휘관 환경에서 **Gemini(앱/스튜디오 등)가 NotebookLM 노트북을 컨텍스트로 묶는** 흐름을 쓸 때, 레포 쪽 **동일 앵커 URL**을 SSOT로 고정한다.

- **역할**: 브리핑·질의·소스 아카이브 레이어. **구현 여부·수치·경로의 단일 진실**은 여전히 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`·호출 가능 스크립트·JSON 산출물(`AGENTS.md` 동일).
- **작전 지휘 참조 노트북 (NotebookLM URL)**  
  - `작전지휘부 Ops20260318` (`347e5cbe-0ade-4615-9aac-8747d4fa644e`) — https://notebooklm.google.com/notebook/347e5cbe-0ade-4615-9aac-8747d4fa644e  
  - `Fusion Insight Hub - Bible x Myeongri x Sasang (2026-04-01)` (`71f55a03-09d0-411f-b365-0ce2a2064c24`) — https://notebooklm.google.com/notebook/71f55a03-09d0-411f-b365-0ce2a2064c24  
- **압축·복원·예언 통합 (FACT 중심, 작전/성경/명리 제외)** — 브리핑·RAG 보조 전용; SSOT는 여전히 레포·`CONSTITUTION`·`artifacts`.  
  - `aba1f8b1-be62-4367-ac7f-b1a997bb77d4` — https://notebooklm.google.com/notebook/aba1f8b1-be62-4367-ac7f-b1a997bb77d4 — 제목: **MKM_CORE_INTELLIGENCE_V1** (MCP `notebook_create` + `source_add`; `.json` 단일 파일 업로드는 도구 제한 시 텍스트 요약·포인터로 대체)
- **LOG_METABOLISM JSONL 정제 전용** — 원시 로그·엄격 프롬프트 산출 JSONL만 적재; `discover_nl_metabolism_source.py`가 `notebooklm_pull_manifest_v1.json`의 `discover_priority_notebook_ids`로 **최우선 스캔**.  
  - `e457f7ae-24b6-49fa-8f3f-1881e5ae027a` — https://notebooklm.google.com/notebook/e457f7ae-24b6-49fa-8f3f-1881e5ae027a — 제목: **MKM_LOG_METABOLISM_REFINERY_V1**
- **CORE ↔ Refinery 교차 질의 보강 (포인터 1파일)** — `docs/final/NOTEBOOKLM_LOG_METABOLISM_CORE_BRIDGE_POINTER_V1.md` 를 **MKM_CORE_INTELLIGENCE_V1** 노트에만 소스 추가 권장(Refinery 노트는 동 문서·CONSTITUTION 이미 보유로 중복 최소화). MCP `cross_notebook_query` 시 CORE 쪽이 LOG_METABOLISM 격벽을 근거로 답하도록 한다.
- **보조 노트북 (지휘관 지정 · B 궤적 / 브리핑·역사 소스)** — 위 메인 앵커를 **대체하지 않음**. 구현·게이트 팩트는 `CONSTITUTION`·`artifacts`·`.py`만.  
  - `978ab6ca-d069-4a78-8916-30c7844c4fa6` — https://notebooklm.google.com/notebook/978ab6ca-d069-4a78-8916-30c7844c4fa6  
  - `d193d8d4-5678-4cc7-8eb6-7046a9a3b16d` — https://notebooklm.google.com/notebook/d193d8d4-5678-4cc7-8eb6-7046a9a3b16d  
  - **로컬 대응(참고):** `H:\workspace\docs\` — 레포 `docs\final` SSOT와 **경로·동일성 보장 없음**; 필요 시 해당 MD를 `@` 첨부.  
- **Vault**: `sync_notebooklm_sources_to_mkm_data_vault.ps1`가 레포 SSOT를 `notebooklm_sources/`로 미러할 때, 에페메럴 핸드오프 `docs/final/CURRENT_OPS_SNAPSHOT.md`도 함께 복사되어 **Hub B / 오프라인 RAG**와 날짜를 맞추기 쉽다.

---

## A 궤적 — **팩트** 소스 (Hard-Fact)

| 우선순위 | 경로 (워크스페이스 기준) | 비고 |
|----------|--------------------------|------|
| P0 | `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` | 헌법 추론 구현 SSOT (**§14 Prism Index** 포함) |
| P1 | `docs/final/MKM12_PRISM_INDEX_REGISTRY_V1.json` | Prism 논리 색인(Grand Indexing 2.0); 경로·역할·`agent_access`; 코드 4D 축과 혼동 금지 |
| P0 | `docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md` | 압축-해석 파이프라인 Fact-Lock SSOT |
| P1 | `docs/final/COMPRESSION_EVALUATE_REPORT_DATA_FLOW_V1.md` | `evaluate_report`·4D 브리지·스윕 CLI 관계(벤치 혼동 방지); 수치는 artifacts 우선 |
| P1 | `docs/final/MKM_LESSONS_LEARNED_V1.md` | 반복 NO_GO 교훈 인덱스(비-SSOT); 구현 팩트는 CONSTITUTION·artifacts |
| P1 | `docs/final/NOTEBOOKLM_LOG_METABOLISM_CORE_BRIDGE_POINTER_V1.md` | NotebookLM **MKM_CORE_INTELLIGENCE_V1** 전용: LOG_METABOLISM·압축 축 격벽 경로 포인터; 구현 SSOT는 CONSTITUTION |
| P1 | `docs/final/INTERNAL_COMPRESSION_MAX_LANE_FOUNDATION_V1.md` | 내부 전용 압축/복원 개발 원점(정경 원어 코어 vs 번역기 레일·조건부 압축·비합선 원칙) |
| P1 | `docs/final/artifacts/MANSE_SAJU_STAGE_LAW_CONTRACT_V0.json` | 만세력·사주 단계 법칙 수학화 계약(v0, 연구 전용·검증 통과분만 freeze) |
| P1 | `docs/final/artifacts/manse_saju_stage_law_spike_latest.json` | 만세력·사주 단계 예측 스파이크 산출(v0, research_only) |
| P1 | `docs/final/COMPRESSION_RESTORATION_EVOLUTION_INDEX_V1.md` | 압축·복원 축 연대기·읽기 순서·`H:\workspace` 병행 근거(비-Git); 수치·GO는 artifacts·스크립트 우선 |
| P1 | `docs/final/MKM_CORE_THEORY_V1.md` | L0/L1/L2 팩트체크에서 **[FACT]만** 추린 압축·복원·예언 축 번들; CONSTITUTION·artifacts 우선 |
| P0 | `docs/final/COMPRESSION_SLA_POLICY_V1.md` | 투트랙 압축 SLA(범용·리터럴)·산출·헬스·웹훅 범위; NotebookLM이 이 수치를 대체하지 않음 |
| P1 | `docs/final/MKM12_L0_L1_L2_CLAIMS_TAGGED_FACTCHECK_2026-04-09.md` | L0/L1/L2 클레임 태그·역추론/사이드 채널 SSOT 인용·외부 문헌 앵커(§I); 운영 통합 여부는 CONSTITUTION·`.py`로만 판정 |
| P1 | `docs/final/openapi_token_compression_stub_v1.yaml` | 토큰 압축 API 스텁 OpenAPI 3 계약 |
| P0 | `docs/final/STATE16_INTERFACE_INSERTION_CONTRACT_2026-03-31.md` | 16상 인터페이스 삽입 계약(비강제·단계 게이트) |
| P0 | `docs/final/MASTER_Linguistic_Contract_2026.md` | 어휘·코퍼스 FACT-LOCK(레일·v2·스테이징) SSOT |
| P0 | `docs/final/master_codebook_dual_track.template.json` | 듀얼 트랙 코드북 템플릿 |
| P0 | `scripts/experimental/codebook_runtime_pack/README.md` | 코드북 런타임 팩 **공식 명칭 SSOT** (`codebook_runtime_pack`), legacy `codepack_recovery`와 구분 |
| P1 | `docs/final/artifacts/codebook_factsafe_bundle_latest.json` | 코드북 팩트세이프 번들 최신 결과(옵션: recovered readiness 포함) |
| P1 | `docs/final/artifacts/recovered_codebook_operational_readiness_latest.json` | 코드북 런타임 팩 운영 준비도 PASS/FAIL 산출 |
| P1 | `projects/bitcoin-trading/ops/.hermes.md` | 외부 부관(Hermes 등) **얇은 프로필**: SSOT 포인터·금지·스킬 앵커; 본문 복제 금지 |
| P1 | `data/regimes/regime_fusion_policy.json` | 레짐 퓨전 정책 |
| P1 | `data/regimes/regime_map.json` | 1차 레짐 맵 |
| P1 | `projects/bitcoin-trading/src/integration/dual_regime_api.py` | dual-regime API |
| P2 | `projects/bitcoin-trading/ops/v2/memory/decision_ledger.py` | 의사결정 ledger |
| P2 | `projects/bitcoin-trading/ops/v2/memory/fact_lock_snapshot.py` | 팩트 스냅샷 |
| P1 | `data/myeongni/myeongni_16_state_experiment_20260329.jsonl` | 명리 16-State 실험 **정본** JSONL (2026-03-29; `state_id` 1–16) |
| P1 | `data/myeongni/16_STATE_MASTER_PROBE_v1.json` | **Master Probe v1** 집계 SSOT (16/16 coverage; NotebookLM/RAG·격벽) |

**확인**: Vault·로컬 경로 정합은 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §7 참조.

### 명리 16-State Master Probe (2026-03-29 정본)

| 항목 | 경로 | 비고 |
|------|------|------|
| 정본 JSONL | `data/myeongni/myeongni_16_state_experiment_20260329.jsonl` | 16줄; 날짜 접미사로 **다른 실험 파일과 혼선 방지** |
| Master Probe 집계 | `data/myeongni/16_STATE_MASTER_PROBE_v1.json` | `coverage_summary.states_with_audit === 16`일 때만 “완전 커버리지”로 서술 |
| 생성기 | `scripts/myeongni_summary_gen.py` | 예: `py scripts/myeongni_summary_gen.py --audit-path data/myeongni/myeongni_16_state_experiment_20260329.jsonl --output data/myeongni/16_STATE_MASTER_PROBE_v1.json` |

**레거시**: `MASTER_PROBE_v1_ACTUAL.json` 등 구버전 이름이 남아 있어도 **SSOT·NotebookLM 인용은 `16_STATE_MASTER_PROBE_v1.json`만** 사용한다.

**격벽**: NotebookLM·RAG 요약·인용 전용. **실매매 트리거·본선 OOF와 자동 합선 금지** (Logos-first·레짐 규칙과 동일하게 “추론 레이어”만).

**NotebookLM — Master Probe 권위 검증 질의 (예시)**

1. 이 워크스페이스에서 **16개 에너지 격자(state 1–16)** 감사·집계의 단일 진실 공급원 파일명과 경로는 무엇인가? (`16_STATE_MASTER_PROBE_v1.json` 우선 인용)
2. `state_id`가 7인 항목의 요약·감사 필드(있다면)를 JSON에서 그대로 인용하라.
3. `myeongni_16_state_experiment_20260329.jsonl`이 아닌 **다른 날짜·다른 접미사**의 실험 파일과 본 정본을 구분하는 한 줄 규칙을 말하라.
4. 작전지휘부 노트북 등 **대량 소스** 없이, `16_STATE_MASTER_PROBE_v1.json`만으로 16-State 지형(커버리지·상태 ID 목록)을 설명할 수 있는가?
5. (코드 리뷰용) JSONL **물리적 줄 번호**가 `state_id`와 같다고 가정하지 말 것 — 근거는 `state_id` 필드와 Master Probe의 `state_ids_present`뿐이라고 요약하라.

---

## B 궤적 — **통찰** 소스 (Insight / Hypothesis)

| 항목 | 경로 (또는 TBD) | 비고 |
|------|------------------|------|
| Track C IP 사업계획 (v1) | `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` | B2B/IP 수익화 실행안; 비투자자문 문구·Track A/B/C 경계 포함 |
| DSS / Qumran | `docs/final/DSS_APOCRYPHA_FRONTLINE_CLOSEOUT_2026-03-27.md` | Creative-Lock; frontline closeout SSOT |
| 명리·융합 의사결정 | `docs/final/MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json` | SSOT; B 노트북에는 동명 텍스트 소스로 반영(`MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json`). A와 역할 분리 |
| AI·명리·만세 외부 참조 | `docs/final/AI_MYEONGNI_MANSE_EXTERNAL_REFERENCE_LANDSCAPE_2026-03-29.md` | 타 서비스·RAG·LLM 패턴 정리(참고만); 본선 OOF·A와 무단 합선 금지 |
| AI-Logos 외부 연구 (arXiv·Kaggle) | `docs/external_research/AI-Logos_Research_Bibliography_2026.md` | B-only; **Confirmed URL** 서지·TBD 분리; 작전 **LeWorld-Enlightenment**; A·본선 자동 합선 금지 |
| Logos 교집합 랭킹 SSOT | `docs/final/LOGOS_INTERSECTION_RANKING_SSOT_2026-03-29.md` | `mean`/`min` 지표·경로; λ(편향)와 기호 분리; 본선·실매매 자동 합선 금지 |
| 한의 원전·프록시 | `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS_Myeongni_Ext.md` · `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §9 | 코퍼스 B 분리·승격 경계; 별도 handoff MD 미작성 시 본 문서가 SSOT |
| 일반예언 — VPS Git + 미래학 딥리서치 융합 번들 | `docs/final/NOTEBOOKLM_GENERAL_PROPHECY_VPS_GIT_FORESIGHT_BUNDLE_2026-04-11.md` | B-only; Git·서지·§7.4 웹 딥리서치·격벽; 일반예언 노트북 `9de651e6-199d-4ea7-88d5-cbca2f177312` |
| 일반 미래 예측 데이터 계약(초안) | `docs/final/GENERAL_PROPHECY_SCHEMA_V1.json` | B-only; `CONSTITUTION` Prophecy 절 포인터; Phase 2–4 스크립트 미구현 |
| BTC 금융 Hub B — A/B 교차검증 브리프 | `docs/final/NOTEBOOKLM_HUB_B_BTC_AB_TRACK_CROSSCHECK_BRIEF_2026-04-04.md` | NotebookLM 소스 ID `bd996cd5-cb6e-444c-8110-eb2ce6a4c745` · 노트북 `b79929a2-8742-42a8-a4d7-06523e12935d` (2026-04-04 적재). OHLCV·온톨로지=B 연구 가설 vs A 본선 팩트 구분·Promotion Loop·Fact-Lock |
| Swarm 심리 메트릭 (B-track 데이터 계약) | `docs/final/SWARM_SENTIMENT_METRIC_SCHEMA_DRAFT.json` · `docs/final/dummy_swarm_score.jsonl` · `[HYPO]` 샘플 `docs/final/hypo_test_sentiment.jsonl` · 듀얼렌즈 1호 `[HYPO]` `docs/final/corr_report_001_hypo.jsonl` + 좌측 참고 `docs/final/corr_report_001_left_lens.json` | MiroFish류 군집 출력→이산 수치 JSON 계약(draft-07); 로컬 검증 `py scripts/validate_swarm_sentiment_dummy.py` 및 `--jsonl …`; 일괄: `scripts/Validate-SwarmSentimentBTrack.ps1`; CI: `swarm-sentiment-schema-validate.yml`; A-track 트리거·실매매 합선 금지 |
| Swarm 메트릭 Hub B 번들 (RAG) | `docs/final/SWARM_SENTIMENT_METRIC_NOTEBOOKLM_BUNDLE_2026-04-04.md` | NotebookLM 금융 Hub B 소스 ID `582bfa0b-ac4d-4715-9073-b170bd7a8719` — JSON 직접 업로드 불가 시 MD 번들로 동일 내용 인제스트 |
| MKMLIFE 뉴스 토픽 · 질문 스타터 | `docs/final/NOTEBOOKLM_MKMLIFE_NEWS_QUESTION_STARTER_BUNDLE_2026-04-12.md` | B-only; 토픽→질문 아이디어만·A/실매매·압축과 격벽; Vault 동기·NotebookLM 인제스트 후 mkmlife UI는 선택 |

### B-Track Major Reference (4D 융합·위성 코퍼스, OBSERVATION_ONLY)

작전지휘부·RAG가 **비교 배경(Comparative Background)** 으로 우선 인용할 B-Track 앵커 묶음. **A-Track·실매매 엔진 기본 로딩·자동 트리거 합선 금지** (`CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §4.5·격벽). `[HYPO]` 서술·승격은 인벤토리 스키마의 `promotion_status` enum(`draft`·`bench_only`·`superseded`·`retired`)만 사용.

| 우선순위 | 경로 | 비고 |
|----------|------|------|
| P0 | `docs/final/artifacts/LOGOS_STATE_MAPPING_V1.json` | 정경 16-state↔verse 코사인 스냅샷; CROSS_REF의 `canonical_ref` 조인 기준 |
| P0 | `docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json` | DSS/외경·위성↔state v2; ENTRY_07·08·16은 line/witness 대기·`note`에 검증 조건 명시 |
| P0 | `docs/final/artifacts/B_TRACK_HYPOTHESIS_INVENTORY_V1.json` | B 가설 인벤토리; `CROSS_REF_DSS_TO_STATES_DRAFT`·`ENTRY_*` 교차 링크 |
| P1 | `projects/dss-4d-ingest/outputs/unified_frontline_cycle_report_command_center_followup_20260327_f.json` | **디스크에 존재하는** frontline 사이클 JSON. 종료 문서가 인용하는 `…_r_ext3` 가 레포에 없을 때 **본 파일을 SSOT**로 삼음 |
| P1 | `docs/final/NOTEBOOKLM_DSS_APOCRYPHA_BUNDLE_NOTE_command_center_followup_20260327_f.md` | DSS/외경 번들 노트(규칙·인사이트 우선순위) |
| P2 | `docs/final/DSS_APOCRYPHA_FRONTLINE_CLOSEOUT_2026-03-27.md` | Frontline closeout 브리핑(위 표 JSON·`_r_ext3` 명명과 불일치 시 **실파일·위 표 우선**) |
| P2 | `docs/final/artifacts/original_corpus_regime_singularity_balanced_report_v1.json` | 레짐별 할당 특이점 B-track(코사인); A·실매매 합선 금지 |
| P2 | `docs/final/artifacts/original_corpus_regime_singularity_report_with_canon_v1.json` | DSS+외경+정경(`verse_decoded_v2`) 레짐 공명 스캔; `top_canon_singularities`=정경 레인만 상위 N |
| P2 | `docs/final/artifacts/original_corpus_regime_singularity_balanced_report_with_canon_v1.json` | 동일 입력에 균형 할당(per-regime quota)·`canon_jsonl` 포함 시 counts.canon_rows |
| P2 | `docs/final/artifacts/original_singularity_gloss_report_v3.json` | 동일 유니온 행 글로스(v3·코드북 브리지·선택 오버라이드); 번역 확정 아님·[HYPO] 보조 |
| P2 | `docs/final/artifacts/original_singularity_gloss_report_v4.json` | v3 스택 + 검증 접두 탈형 체인(표면 길이 우선 첫 매핑); 공격적 정규화 금지·[HYPO] 보조 |
| P2 | `docs/final/artifacts/hebrew_singularity_gloss_overrides_v1.json` | 분석자 오버라이드(단편/DSS 형태 등); [HYPO] |
| P2 | `docs/final/artifacts/master_codebook_lexicon_v1_export_pointer_latest.json` | 최신 `master_codebook_lexicon_v1_*_rows_latest.json` 포인터(행 수·atoms 입력 SHA); 대용량 lexicon 본체는 `reports/constitution/btrack_pilot/` |

### B 보조 — Obsidian Context (Creative-Lock, 로컬 볼트)

**목적**: 레포·`docs/final`에 없는 **지휘관 의도·초안·런북 맥락**을 NotebookLM/Vault 미러에 올릴 때 사용. **A(Fact-Lock)를 대체하지 않음.** 민감·미완료·내부 은어는 선별·비식별 후 반영.

**로컬 SSOT 경로**: `memory/obsidian_vault/` (주 볼트; `AGENTS.md` 동일)

| 카테고리 (v4.7 매핑) | 실제 워크스페이스 경로 (디렉터리는 `*.md`만 Vault로 미러) | 비고 |
|----------------------|----------------------------------------------------------|------|
| 코어·대시보드 | `memory/obsidian_vault/00_Project_Core/` | S-L-K-M·12 도메인 대시보드 등 |
| 전략·연구 초안 | `memory/obsidian_vault/raw_research/` | 로드맵·NotebookLM·Kaggle·마케팅 메모 다수 |
| OPS·엔지니어링 | `memory/obsidian_vault/OPS/`, `memory/obsidian_vault/CODING/` | 런북 성격 |
| Theology / Logos 에세이 | `memory/obsidian_vault/SPIRIT/` | 일지·성찰 계열( B 궤적 ) |
| 시장·트레이딩 | `memory/obsidian_vault/TRADING/`, `memory/obsidian_vault/RESEARCH/` | 일지·리서치 |
| NotebookLM 인덱스 | `memory/obsidian_vault/NotebookLM*.md` (볼트 루트, 파일명 패턴) | 스크립트가 동적 매칭 |

**제외(동기화 스크립트)**: `.obsidian/`, `_cursor_session_staging/` (설정·스테이징 노이즈)

**Vault 미러 출력**: `G:\공유 드라이브\MKM_DATA_VAULT\vault\obsidian_context\` (또는 `MKM_VAULT_ROOT\obsidian_context\`) — `sync_notebooklm_sources_to_mkm_data_vault.ps1 -IncludeObsidianContext`

**소스 경로 오버라이드**: 실제 볼트가 레포 밖이면 환경 변수 `MKM_OBSIDIAN_VAULT_ROOT` 또는 같은 스크립트의 `-ObsidianVaultRoot`로 볼트 루트를 지정한다. 미지정 시 기본은 `<workspace>/memory/obsidian_vault`(`.gitignore`로 클론에 없을 수 있음); 첫 동기 시 해당 경로에 매니페스트 하위 폴더 스텁이 만들어진다.

---

## 이제마_B_Track (분리 원칙)

**원칙**: 라벨 코호트 **A**와 원전·프록시 코퍼스 **B**를 분리. **B를 본선 OOF에 자동 합선하지 않음.**

**인벤토리 기준일**: 2026-03-29 (`data/corpus/ijeoma/_inventory` 등).

### B 핵심 파일 (NotebookLM file 소스 7) — Vault 동기화 + NotebookLM `source_add` 권장

워크스페이스에 존재. **Source-Boost (2026-03-29)** + **AI-Logos 서지 (2026-03-29)** + **Deep Past Kaggle URL (2026-03-29)**: `notebook_get` 기준 B = **파일 소스 7** + **arXiv URL 3** + **Kaggle URL 3** + **Wikipedia URL 8** = **총 21**.

| # | 경로 | NotebookLM `source_id` (ingested) | 비고 |
|---|------|-----------------------------------|------|
| 1 | `data/corpus/ijeoma/originals/jeokcheonsu_core_logic_chunk.md` | `1b40f632-3a46-4fc2-9570-64f8c585817e` | 《적천수》맥락·일간 강약 스캐폴드(B-only; A·OOF 자동 합선 금지) |
| 2 | `data/corpus/ijeoma/schemas/myeongni_fusion_schema_v2_draft.md` | `cab11051-b771-4698-8ef3-70fb556a19d0` | JSON 스키마 v2 초안 MD(B 노트북에 업로드한 경로; SSOT) |
| 3 | `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS_Myeongni_Ext.md` | `24123e98-0a14-4a4c-9a4f-fbe7a53c198c` | B 전용 추론 경계 |
| 4 | `docs/final/myeongni_fusion_schema_v2_draft.md` | — | (2)와 동일 초안의 **문서 미러**; NotebookLM에는 **(2)만** 올려 중복 방지 |
| 5 | `docs/final/MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json` | (기존 B 등록) | 명리 융합 의사결정 JSON; B에 동명 파일 소스로 기존 반영 |
| 6 | `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` | — | §9 A/B 분리·구현 팩트; A 노트와 역할 구분 유지 |

### B 보조·인벤토리 (NotebookLM·Vault 동기화 시)

| 경로 | 비고 |
|------|------|
| `data/corpus/ijeoma/_inventory/IJEOMA_NOTEBOOKLM_QUERY_SET_2026-03-29.md` | 쿼리 세트 |
| `data/corpus/ijeoma/_inventory/IJEOMA_INSIGHT_UNITS_XINGMING_SAMPLE_2026-03-29.json` | 통찰 단위 샘플(JSON) |
| `data/corpus/ijeoma/_inventory/IJEOMA_INSIGHT_UNITS_SASANG_FOUR_SAMPLE_2026-03-29.json` | 사상 사본 샘플(JSON) |
| `data/corpus/ijeoma/_inventory/IJEOMA_CODEBOOK_INDEX_DRAFT_2026-03-29.json` | 코드북 인덱스 초안 |
| `data/corpus/ijeoma/e_drive_mirror/donguisusebowon_mastery_report.md` | 동의보감 마스터리 보고서(NotebookLM 소스) |

### 마스터·청크·인벤토리 (대용량·선택)

| 경로 | 비고 |
|------|------|
| `data/corpus/ijeoma/_inventory/IJEOMA_MASTER_MANIFEST_DRAFT_2026-03-29.json` | 마스터 매니페스트 초안 |
| `data/corpus/ijeoma/_inventory/IJEOMA_CHUNK_TABLE_2026-03-29.jsonl` | 청크 테이블 |
| `data/corpus/ijeoma/_inventory/IJEOMA_CORPUS_INVENTORY_2026-03-28.json` | 코퍼스 인벤토리 |
| `data/corpus/ijeoma/_inventory/hwp_com_export_report.json` | HWP/COM보내기 리포트 |

### 통찰→팩트 후보 (승격 전 확인)

| 통찰→팩트 후보 | 제안 경로 또는 조건 | 비고 |
|----------------|---------------------|------|
| DSS Apocrypha proxy handoff 등 | `docs/final/DSS_APOCRYPHA_FRONTLINE_CLOSEOUT_2026-03-27.md` | 본선 편입 전 A SSOT 갱신·검토 |

---

## Logos_MKM / Logos-Insight

**메타 가이드**: `docs/final/LOGOS_NOTEBOOK_META_GUIDE.md`

**용어 (L2 브리핑)**: “Logos Lens / Ruleset” 표기는 구현·산출물 **로고스 독립 렌즈**와 동일 계열로 본다 — `logos_independent_lens` → `docs/final/artifacts/logos_independent_lens_latest.json`, `scripts/run_lens_logos.py`, `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 표.

| 우선순위 | 경로 (워크스페이스 기준) | 비고 |
|----------|--------------------------|------|
| P0 | `docs/final/LOGOS_NOTEBOOK_META_GUIDE.md` | Logos-Insight 경계(금융/레짐 비혼선) |
| P0 | `docs/final/LOGOS_RISK_BRIDGE_v1.md` | Logos–시장 심리·레짐 **메타** 브리지(가설·v1; verse 파이프와 분리) |
| P0 | `data/logos/verse_4pipeline_full_31102.json` | 4D verse 풀(31102절) |
| P0 | `data/logos/bible_original_hebrew_greek.jsonl` | 원어 라인 |
| P1 | `data/logos/manuscripts/dss_parsed.jsonl` | 사해사본 파싱 JSONL (Logos GPU·벤치 `--include-dss-apocrypha`) |
| P1 | `data/logos/manuscripts/apocrypha_std.jsonl` | 외경 표준 JSONL (동일) |
| P1 | `data/logos/bible_original_verses.jsonl` | 원문 절 라인 |
| P1 | `data/logos/bible_original_for_decode.jsonl` | 복호·해석용 |
| P1 | `data/logos/aruljohn_kjv/` | KJV per-book JSON |
| P2 | `data/logos/reports/ensemble_core_v1_1.csv` | Core 앙상블 CSV(기술 서술 시 **311** 구절) |
| P2 | `data/logos/reports/logos_core_verses_20260315.md` | Core 구절 MD |
| P2 | `data/logos/reports/logos_wide_20_for_notebooklm.json` | Wide 20 권보내기(JSON) |
| P2 | `data/logos/reports/logos_wide_20_for_notebooklm.csv` | Wide 20 권보내기(CSV) |
| P2 | `data/regimes/btc_regime_map.json` | BTC 레짐 맵(`scripts/logos_vector_resonance_probe.py` `--rank-by-regime` FULL 시 입력) |
| P2 | `backtest_results/LOGOS_RESONANCE_BTC_BULL_FULL.json` | canon-only FULL 공명(BULL); `verses_scanned` 31102; 스키마 `logos_resonance_probe_v2` |
| P2 | `backtest_results/LOGOS_RESONANCE_BTC_BEAR_FULL.json` | canon-only FULL 공명(BEAR); 동일 |
| P2 | `backtest_results/LOGOS_RESONANCE_BTC_SIDEWAYS_FULL.json` | canon-only FULL 공명(SIDEWAYS); 동일 |
| — | `.cursor/rules/logos-first-pipeline.mdc` | 근원(Logos)과 확장 레이어 분리 |

**확장 후보(용량·라이선스 검토 후)**

- `data/logos/bibles/hebrew_bhs_sanitized.jsonl`
- `data/logos/bibles/greek_septuagint_public.md`
- `data/logos/bibles/kjv_public_domain.txt`
- `data/logos/manuscripts/dead_sea_scrolls_summary.md` — 요약·가이드; **본선 JSONL SSOT는** `dss_parsed.jsonl`
- `data/logos/manuscripts/apocrypha_guide.md` — 요약·가이드; **본선 JSONL SSOT는** `apocrypha_std.jsonl`
- **보류(미작성)**: `docs/final/LOGOS_PIPELINE_SPEC_V1.md`, `docs/final/GEMATRIA_CODEBOOK_CONCEPT.md` — 현재 워크스페이스에 **파일 없음**. 대체 SSOT: `docs/final/LOGOS_NOTEBOOK_META_GUIDE.md`, `docs/final/LOGOS_RISK_BRIDGE_v1.md`, `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`. 독립 스펙이 생기면 본 표에 경로만 추가(중복 MD 남발 금지).

---

## 통찰 승격 (Promotion Loop)

1. B에서 가설·통찰 산출.  
2. 검증·편집 후 팩트/코드북/레짐 정책에 반영.  
3. `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`에 **구현·경로** 갱신 시 A 궤적·Cursor 규칙과 정합 유지.

---

## 작전지휘부(Ops) NotebookLM 메모 (2026-04-03)

- **2026-04-03 L2 Logos KOSPI Shadow 동기화**: Vault 미러에 다음이 포함됨 — `docs/final/NOTEBOOKLM_OPS_COMMAND_BRIEF_LOGOS_SHADOW_2026-04-03.md`(상황·NotebookLM 질의 세트), `docs/final/artifacts/LOGOS_SHADOW_202003_INSIGHT_BRIEF_V1.md`, `docs/final/artifacts/logos_kospi_shadow_evaluation_bundle_v23_notebooklm.md`(v23 번들 JSON의 Markdown 래퍼; NotebookLM 파일 업로드는 `.json` 미지원 사례 대비). SSOT 수치는 여전히 `reports/research/logos_shadow_v1/logos_kospi_shadow_evaluation_bundle_v23_latest.json`. 작전지휘부 노트북에는 MCP `source_add`(동일 제목 구버전 있으면 `source_delete`로 정리 후) 권장.
- **2026-04-03 (브리지 정정)**: `NOTEBOOKLM_OPS_COMMAND_BRIEF_LOGOS_SHADOW_2026-04-03.md`에 **`--bare` vs `DEFAULT_SHADOW_EXTRA`(latest)** 이중 스냅샷과 SSOT 주의문을 반영함. 문서만 보고 “전 구간 미통과”로 단정하지 말 것.
- **2026-04-03 (v23 MD 래퍼)**: `docs/final/artifacts/logos_kospi_shadow_evaluation_bundle_v23_notebooklm.md`는 `v23_latest.json`과 불일치 시 `py scripts/regen_logos_kospi_shadow_v23_notebooklm_md.py`로 재생성. 일괄: `pwsh -File scripts/Invoke-LogosKospiShadowNotebooklmBundle.ps1` (옵션 `-SyncVault`). Ablation 요약은 `reports/.../logos_kospi_shadow_ablation_v23_round1_summary.json`(Vault 동기화 목록에 포함).
- **NotebookLM**: 노트북명 `작전지휘부 Ops20260318`, ID `347e5cbe-0ade-4615-9aac-8747d4fa644e`, 소스 **13**개 (`notebook_list` 2026-04-02 재확인). 과거 중복 제거 이력(230→151)은 보존하되, 운영 판단 시에는 **현재 MCP 조회값**을 우선한다.
- **전체 wipe**: **기본 금지**. 소스 대량 삭제는 사용자가 **명시적으로 재구축·전체 재업로드**를 요청한 경우에만 수행.
- **`OPS_ONEPAGE_STATUS_LATEST.md`**: 워크스페이스 `docs/final/OPS_ONEPAGE_STATUS_LATEST.md`는 **미존재**할 수 있음. NotebookLM에는 소스 **제목**으로만 존재할 수 있음. 새 MD 남발 대신 `docs/final/` 기존 SITREP·본 매니페스트에 **Gap 한 줄** 기록.
- **로컬 브리지 문서**: `docs/작전지휘부/` 등 경로는 **Vault·다른 머신에만** 있을 수 있음. `source_add` 전 **파일 존재 확인** 필수.

### 파일 기반 장기기억(.mkm-memory) — 멀티렌즈 압축·4D 동기화 (A, 2026-04)

- **역할**: NotebookLM 질의 시 **본 절 + 아래 경로**를 `source_add`하면 작전지휘부 노트에서 **B/High·B/Ultra·A/Extreme 파일럿·재색인 절차**를 근거로 답할 수 있음(측정값은 레포 JSON이 SSOT).
- **파일럿 실행**: `scripts/pilot_compress_mkm_memory_queue.py` — `reports/memory/mkm_memory_priority_queue_latest.json` 기준; P1 헤드 스윕 산출 예: `mkm_memory_pilot_sweep_ultra_latest.json`, `mkm_memory_pilot_conservative_p1head_latest.json`.
- **비교 매트릭스**: `reports/memory/mkm_memory_pilot_sweep_matrix_latest.json`.
- **`content` 변경 후 `vector_4d`**: 동기화 필수 — `tools/tools/core/file_based_memory.py`(`hybrid_vectorize`) 및 `reports/memory/mkm_memory_vector_4d_reindex_paths_v1.json` 참조. `scripts/normalize_mkm_memory_vector_4d.py`는 **중첩 필드 호이스트**용이며 **새 텍스트 재임베딩 대체 아님**.
- **운영 GO/NO_GO**: `reports/memory/mkm_memory_ultra_compression_go_checklist_v1.json` + `reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json` + `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json` **교차** (민감 무결성·카나리·`go_no_go`).
- **격벽**: 파일럿 수치(A)와 NotebookLM 서술(B) 혼동 금지; 본선 `memory/` **인플레이스 쓰기**는 승인·백업·롤백 게이트 후 — `reports/memory/mkm_memory_rollout_gates_v1.json`.

---

## 만세력·사주 NotebookLM (A/B 참조)

**역할**: **A = Fact-Lock(제품·팩트)**, **B = Creative-Lock(연구·통찰)**. 작전지휘부·Logos와 동일하게 **전체 wipe 지양**, 파일 단위 `source_add`만.

| 구분 | NotebookLM 노트북 ID (참고) | 비고 |
|------|-----------------------------|------|
| A (팩트) | `31e6d45a-4a0e-40e6-a010-9c03a6ec1239` | 표 ID와 일치 (`notebook_get` 2026-03-29 검증). **계정·프로필 전환 시** UI 또는 `notebook_get`으로 재확인 |
| B (통찰) | `af639d3e-b455-4f3f-8e25-47f58d962c60` | 동일 |

**MCP 검증 (2026-03-29, 현재 계정)**: `notebook_get` 성공 — A 제목 `만세력·사주_AI_A_제품 (MKM Fact-Lock)`, 소스 **7**개; B 제목 `만세력·사주_AI_B_연구 (MKM Abstract)`, 소스 **21**개(파일 7 + arXiv 3 + Kaggle 3 + Wikipedia 8). **Source-Boost ([A] 경로, 2026-03-29)** + **AI-Logos 번들 URL·서지** + **Deep Past Initiative Kaggle `source_add`** 반영 후 **`notebook_get` 재확인** — B 총 **21**.

**장부 최종 동기화 (`notebook_get` 재실측, 2026-03-29, Operation [B])**: `notebook_id` `af639d3e-b455-4f3f-8e25-47f58d962c60` — `source_count` **21** (Deep Past Kaggle URL 엔트리 추가). 아래 표는 API 반환 **`title`·`id` 원문**으로 SSOT 박제(위키·Kaggle 표시명은 UI와 동일).

**B — AI-Logos 외부 연구 번들 (LeWorld-Enlightenment, 2026-03-29)** — arXiv·Kaggle **URL** + 로컬 서지 MD `source_add` 후 **`notebook_get`으로 소스 수 재확인** (아래는 Confirmed 링크만; “Project Enoch” 등 미검증 주장은 **서지 TBD**).

| 구분 | URL |
|------|-----|
| [PAPER] LeWorldModel | `https://arxiv.org/abs/2603.19312` |
| [PAPER] DSS ink/parchment segmentation | `https://arxiv.org/abs/2411.10668` |
| [PAPER] DSS writer ID (1QIsaa) | `https://arxiv.org/abs/2010.14476` |
| [KAGGLE] Vesuvius ink detection | `https://www.kaggle.com/competitions/vesuvius-challenge-ink-detection` |
| [KAGGLE] CommonLit readability (텍스트 회귀 참고) | `https://www.kaggle.com/competitions/commonlitreadabilityprize` |
| [KAGGLE] Deep Past Initiative (Akkadian→English MT) | `https://www.kaggle.com/competitions/deep-past-initiative-machine-translation` — **NotebookLM URL 소스** `f0cbb85f-b5bf-4ec5-b958-4c690d282a01` (제목: Deep Past Challenge - Translate Akkadian to English \| Kaggle). 서지 `AI-Logos_Research_Bibliography_2026.md`와 병행. |

- **로컬 서지 (file)**: `C:\workspace\docs\external_research\AI-Logos_Research_Bibliography_2026.md` — `source_type: file`, `wait: true`.

**B 노트 전체 소스 (Fact-Locked, `notebook_get` 2026-03-29)** — `source_count` = **21** (API `sources` 순서):

| # | `source_id` | `title` (API) |
|---|-------------|---------------|
| 1 | `c0835f38-3442-4556-8c6d-d482218c5160` | AI-Logos_Research_Bibliography_2026.md |
| 2 | `c8c33f64-1591-4e27-9c79-6ac7f467b28f` | AI_MYEONGNI_MANSE_EXTERNAL_REFERENCE_LANDSCAPE_2026-03-29.md |
| 3 | `24123e98-0a14-4a4c-9a4f-fbe7a53c198c` | CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS_Myeongni_Ext.md |
| 4 | `0936b481-8411-462a-bc84-f31b2e67a0f3` | Chinese calendar - Wikipedia |
| 5 | `8040cf3b-9788-48e3-81c8-585479747f8a` | CommonLit Readability Prize \| Kaggle |
| 6 | `f0cbb85f-b5bf-4ec5-b958-4c690d282a01` | Deep Past Challenge - Translate Akkadian to English \| Kaggle |
| 7 | `7397498f-ae59-42eb-bc13-743cd685bbbb` | Four Pillars of Destiny - Wikipedia |
| 8 | `7d7417ac-0adc-4d9f-9dd9-21e60fb5f91c` | Korean calendar - Wikipedia |
| 9 | `b7af7a11-d243-4f0f-ab7b-15b99a51a1cd` | Lunisolar calendar - Wikipedia |
| 10 | `0c755abd-592d-4347-9306-3226380b5934` | MANSE_SAJU_AI_RESEARCH_SYNTHESIS_2026-03-29.md |
| 11 | `77ae458c-259f-4e92-ad12-ae5e2bd650f8` | MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json |
| 12 | `cc9dd0b9-393b-4f0a-a458-6c48b7ada4f5` | Sexagenary cycle - Wikipedia |
| 13 | `45bc0dac-0b90-4786-9474-58fcfc1708a1` | Vesuvius Challenge - Ink Detection \| Kaggle |
| 14 | `0939abb4-73dc-49e4-aee7-75518fd5e410` | [2010.14476] Artificial intelligence based writer identification generates new evidence for the unknown scribes of the Dead Sea Scrolls exemplified by the Great Isaiah Scroll (1QIsaa) |
| 15 | `f4a61719-9678-46c6-be81-302e003dd99b` | [2411.10668] Segmentation of Ink and Parchment in Dead Sea Scroll Fragments |
| 16 | `794cf83b-4bce-4452-82fc-55b279be31a8` | [2603.19312] LeWorldModel: Stable End-to-End Joint-Embedding Predictive Architecture from Pixels |
| 17 | `1b40f632-3a46-4fc2-9570-64f8c585817e` | jeokcheonsu_core_logic_chunk.md |
| 18 | `cab11051-b771-4698-8ef3-70fb556a19d0` | myeongni_fusion_schema_v2_draft.md |
| 19 | `a60a8dc9-9ec3-4235-ac7d-0a8618f903d6` | 만세력 - 위키백과, 우리 모두의 백과사전 |
| 20 | `f1403d37-9616-408f-aae0-8404a80abc0b` | 사주 - 위키백과, 우리 모두의 백과사전 |
| 21 | `1291ea4c-53a7-43bd-8fb1-892a9e8b143d` | 사주명리학 - 위키백과, 우리 모두의 백과사전 |

**A 노트 소스 제목 (요약, `notebook_get`과 동일)** — 카운트 **7**; 상세 ID 목록은 필요 시 동일 절차로 `notebook_get`(`31e6d45a-4a0e-40e6-a010-9c03a6ec1239`) 실측.

**B — Wikipedia URL SSOT (`source_add` 2026-03-29)** — 통찰·참고 전용; 본선 OOF·A와 무단 합선 금지.

```
https://en.wikipedia.org/wiki/Four_Pillars_of_Destiny
https://en.wikipedia.org/wiki/Korean_calendar
https://en.wikipedia.org/wiki/Sexagenary_cycle
https://en.wikipedia.org/wiki/Lunisolar_calendar
https://en.wikipedia.org/wiki/Chinese_calendar
https://ko.wikipedia.org/wiki/%EC%82%AC%EC%A3%BC
https://ko.wikipedia.org/wiki/%EB%A7%8C%EC%84%B8%EB%A0%A5
https://ko.wikipedia.org/wiki/%EC%82%AC%EC%A3%BC%EB%AA%85%EB%A6%AC%ED%95%99
```

**명리 스키마 B 반영 (2026-03-29)**: SSOT는 `docs/final/MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json`. 파일 소스 `source_add`가 실패한 경우 **`source_type: text`**로 본문 전체 업로드 가능 — B에 `MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json` 제목으로 등록됨(`source_id` `77ae458c-259f-4e92-ad12-ae5e2bd650f8`). 구현·경로 팩트는 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §7과 정합 유지.

**소스 경로 SSOT**: 워크스페이스에 `docs/작전지휘부/CURSOR_CHAT_NOTEBOOKLM_COMMAND_BRIDGE_2026-03-28.md`가 **있을 때** 해당 MD의 `[FACT] 만세력·사주 이원 노트` 블록을 우선. **없으면** 본 매니페스트 **A/B 궤적** 표와 사용자가 지정한 경로만 사용. **`scripts/push_manse_saju_notebooklm_from_manifest.ps1`는 존재하지 않음** (벌크 푸시 스크립트 금지).

**갱신 절차**: `notebook_get` → 갱신할 파일 `Test-Path` → MCP `source_add`(`source_type: file`, `file_path`, `wait: true`).

---

## B-Track — 사해(DSS)와 외경 순차 작업 (권장 운영, 2026-03-30)

**목적**: 노트북 한 곳에 DSS·외경을 **처음부터 한꺼번에 융합**하면 출처·인용이 섞여 통찰 품질이 떨어지기 쉬움. **비트코인·16상 매핑 없이** 순수 문헌 통찰만 뽑을 때도 동일 원칙 적용.

| 단계 | 범위 | NotebookLM 조작 |
|------|------|-----------------|
| **1** | **DSS·쿰란만** (1QM, 1QS, 페셔 등) | **별도 노트** 권장(예: 제목에 `DSS-only`). 소스는 아래 DSS Fusion 표의 MD·URL 중 DSS에 해당하는 것만 우선. 질의마다 *「지금은 사해/쿰란 사본만 인용」* 문구 명시. |
| **2** | **외경·유경만** (1에녹, 희년서, 마카베오기 등) | **다른 노트**로 분리(예: `Apocrypha-only`). 1단계 노트와 소스를 섞지 않음. 번역·요약 MD 청크를 `source_add`할 때도 코퍼스별로 나눔. |
| **3 (선택)** | 두 전통 **대조** | 1·2에서 내보낸 **요약·핵심 구절 표**만 세 번째 노트에 모으거나, Cursor 채팅에 투하하여 대조. **기존 DSS Fusion 번들 노트**(`2b2eeff1-…`)는 참고·아카이브용; 순차 1·2와 혼동되면 **새 노트**가 더 안전. |

**금지(권장 수준)**: 1단계 미완에 2단계 소스를 같은 노트에 대량 추가하여 *즉시* “통합 사상” 질의만 하는 방식 — 인용 혼선 유발.

**격벽**: 본 절은 **NotebookLM·연구 워크플로** 안내. 정경 31,102 파이프라인·A-Track 실매매 코드와 **자동 합선 없음** (`CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 멀티 코퍼스 표와 동일).

**MCP 자동 생성 노트 (2026-03-30, `notebook_create` + `source_add`; 이후 보강 반영)**

| 노트 제목 | `notebook_id` | URL | `source_count` / 비고 (2026-03-30 갱신) |
|-----------|---------------|-----|----------------------------------------|
| B-Track DSS-only (Qumran) 2026-03-30 | `3839cf65-d97c-465c-a252-7ca9441af201` | `https://notebooklm.google.com/notebook/3839cf65-d97c-465c-a252-7ca9441af201` | **`notebook_get` 실측 10** (2026-03-30) — 스코프·메타·리스크·DSS 아카이브 URL·arXiv 2건·`btrack_dss_1QM_col1_excerpt.md`·`btrack_dss_1QS_sectarian_context.md`·`btrack_dss_1QS_pure_discipline.md` |
| B-Track Apocrypha-only 2026-03-30 | `17ab44ab-0f62-4714-99ac-12688a469597` | `https://notebooklm.google.com/notebook/17ab44ab-0f62-4714-99ac-12688a469597` | **`notebook_get` 실측 10** (2026-03-30) — 동일; **`btrack_apocrypha_jubilees_calendar_364.md` NL 재동기화**(구 소스 삭제 후 최신 로컬 재`source_add`, 2026-03-30)로 Charlesworth·1에녹 72–82 병치 문단 인덱스 확인 |
| B-Track Phase3 Contrast (exports only) 2026-03-30 | `aced4a3e-6ece-4770-b46d-46e1454da893` | `https://notebooklm.google.com/notebook/aced4a3e-6ece-4770-b46d-46e1454da893` | **`notebook_get` 실측 2** — `Phase3 — 사용법…` + **`btrack_phase3_cross_ref_snapshot.md` 재동기화**(구 `cc37772c…` 삭제 → 신 `4a76d12a…`, ENTRY_01–10·`generated_at_utc` JSON 정합, 2026-03-30) |

---

## DSS Fusion Sources (DSS + 외경)

**역할**: DSS·외경(Apocrypha) 번들·리스크·구현 팩트를 한 노트에 모음. **JSONL**은 NotebookLM 파일 업로드가 실패할 수 있으므로 **`docs/final/*.md`** 위주로 `source_add`.

| 항목 | 값 |
|------|-----|
| **제목** | DSS Fusion Sources 2026-03-26 |
| **notebook_id** | `2b2eeff1-1bac-424c-9128-59d0f0946908` |
| **URL** | `https://notebooklm.google.com/notebook/2b2eeff1-1bac-424c-9128-59d0f0946908` |

**`notebook_get` 검증 (2026-03-29)**: `source_count` **8**.

**[Deduplication-Audit] (2026-03-29)**: 본 노트(`2b2eeff1-1bac-424c-9128-59d0f0946908`) 및 **만세력·사주 B**(`af639d3e-b455-4f3f-8e25-47f58d962c60`, `source_count` 21)에 대해 `notebook_get` 실측 후 **정규화 제목**(앞뒤 공백 제거·연속 공백 통일) 기준 **완전 동일 쌍 없음**. 참고: DSS 노트 URL 2건은 *The Dead Sea Scrolls* vs *The Dead Sea Scrolls - Explore the Archive*로 **문자열이 달라** 엄격 중복 아님(의미상 근접 시 수동 병합은 선택).

| 소스 제목 (표시명) | 비고 |
|-------------------|------|
| `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` | 구현 팩트 SSOT |
| `DSS_APOCRYPHA_FRONTLINE_CLOSEOUT_2026-03-27.md` | DSS·외경 프론트라인 클로즈아웃 |
| `LOGOS_NOTEBOOK_META_GUIDE.md` | 노트북 메타 가이드 |
| `LOGOS_RISK_BRIDGE_v1.md` | 리스크 브리지 |
| `NOTEBOOKLM_DSS_APOCRYPHA_BUNDLE_NOTE_command_center_followup_20260327_f.md` | 번들 노트 |
| *(URL)* GitHub - ETCBC/dss … | Abegg/TF 참조 |
| *(URL)* The Dead Sea Scrolls | 외부 DSS |
| *(URL)* The Dead Sea Scrolls - Explore the Archive | 아카이브 탐색 |

**`source_add` 로컬 파일 확정 (2026-03-29, `Test-Path` 전부 True)** — NotebookLM MCP `source_type: file` 시 `file_path` 예시:

| # | `file_path` (Windows) |
|---|------------------------|
| 1 | `C:\workspace\docs\final\CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` |
| 2 | `C:\workspace\docs\final\DSS_APOCRYPHA_FRONTLINE_CLOSEOUT_2026-03-27.md` |
| 3 | `C:\workspace\docs\final\LOGOS_NOTEBOOK_META_GUIDE.md` |
| 4 | `C:\workspace\docs\final\LOGOS_RISK_BRIDGE_v1.md` |
| 5 | `C:\workspace\docs\final\NOTEBOOKLM_DSS_APOCRYPHA_BUNDLE_NOTE_command_center_followup_20260327_f.md` |

위 5개는 **MD·SSOT**로 DSS Fusion 노트와 정합; **JSONL**은 업로드 실패 가능성이 있어 본 노트의 직접 소스로는 권장하지 않음.

**원시 코퍼스** (`data/logos/manuscripts/*.jsonl`)는 노트에 직접 붙이기 어려울 수 있음 → 필요 시 **MD/TXT 청크** 또는 **PDF**로 내보낸 뒤 `source_add file`.

---

## 차기 작업 (Gap)

- **Blind Replay C.1 (2026-04-02)**: ✅ Phase C.1 피처 확장 산출물 반영 완료 — `BLIND_REPLAY_PROXY_PROFILE_D_PARAMS_V1.json`, `BLIND_REPLAY_PROXY_PROFILE_D_ENSEMBLE_SEARCH_V1.json`, `aegis_unified_scoreboard_abcds_latest.json`, `blind_replay_dataset_grid_btc_s80_latest.json`, `blind_replay_dataset_grid_kospi_s80_latest.json`를 NotebookLM 동기화 스크립트 복사 목록에 추가.
- **B — AI-Logos 번들**: ✅ `source_add`(URL 5 + file 서지) 반영·**`notebook_get` B=21** 확인(2026-03-29; Deep Past Kaggle URL 추가). ✅ 서지에 **arXiv 2407.12013(Enoch)**·**deeppast.org** Confirmed 반영(2026-03-29). ✅ Deep Past **Kaggle 대회 URL**: 서지 `AI-Logos_Research_Bibliography_2026.md` + **NotebookLM URL 소스** `f0cbb85f-b5bf-4ec5-b958-4c690d282a01` (`source_add`, 2026-03-29). ✅ **Operation [B] 장부**: 매니페스트에 B 노트 **21개 전체** `source_id`·`title` 실측 표 박제(2026-03-29).
- **B — `notebook_query` (노트 `af639d3e-b455-4f3f-8e25-47f58d962c60`)**: Q1/Q2 Gap 유지. ✅ **후속 적층 질의**(LeWM 초록 ↔ DSS 세그멘테이션·필적 식별 대조, 사실/가설 표·비유 한계) `conversation_id` **`deb0fc0c-5e20-4041-a917-0fe240f0b2bb`**로 실행·응답 수신(2026-03-29); 인용 소스 ID: `794cf83b-…`(LeWM), `f4a61719-…`(2411.10668), `0939abb4-…`(1QIsaa).
- **Logos BTC 공명**: canon-only **BULL/BEAR/SIDEWAYS FULL** 산출물은 본 매니페스트 Logos 표에 등록됨. **Ancient-expanded**(`--ancient-resonance`)는 별도 파일명으로 실행·등록(캐논 FULL 시리즈와 혼선 금지).
- **이제마 B**: Source-Boost·AI-Logos 번들·Deep Past Kaggle URL 반영·`notebook_get` B=21 확인 후 — 통찰 품질·중복 소스 점검, 필요 시 Vault `sync_notebooklm_sources_to_mkm_data_vault.ps1`. `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §9·B 표와 정합 유지.  
- **명리**: SSOT `MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json`는 B에 동기화됨; MD 스키마 초안은 `data/corpus/ijeoma/schemas/myeongni_fusion_schema_v2_draft.md`(B 노트 등록)와 `docs/final/myeongni_fusion_schema_v2_draft.md`(미러). 본선 OOF·실매매 트리거 자동 연동은 **헌법·팩트 문서에서 명시된 구현 경로가 있을 때만** — 스키마만으로 자동 합선하지 않음.
- **Master Probe (2026-03-29)**: ✅ 매니페스트 **A 궤적** 및 **§명리 16-State Master Probe**에 `data/myeongni/16_STATE_MASTER_PROBE_v1.json`·`data/myeongni/myeongni_16_state_experiment_20260329.jsonl` 경로·격벽·검증 질의 SSOT 박제. 차기(선택): 대상 노트북에 `source_add`(file)로 JSON 주입 후 본문 §검증 질의로 권위 응답 확인.

---

**상태**: A 궤적 · Logos-Insight 표(wide_20 JSON/CSV 포함) · **BTC 레짐 공명 FULL JSON 3종·btc_regime_map** 매니페스트 반영 · 이제마 B 분리 · 작전지휘부 151 소스·wipe 정책 · 만세력·사주 A/B `notebook_get` 검증 완료(표 ID 일치; **B 소스 21개**·파일 7·arXiv 3·Kaggle 3·위키 8·AI-Logos 서지·명리 스키마·외부 참조 랜드스케이프·Deep Past Kaggle URL) · **B `notebook_query`** 소스-바운드 Q1/Q2 Gap 기록(2026-03-29) · **DSS Fusion** 노트(`2b2eeff1-…`) 소스 8개 검증 · OPS_ONEPAGE Gap 기록 정책 · **Master Probe v1 / 16-State 정본(2026-03-29) 매니페스트 SSOT** (2026-03-29)
· **Codebook Runtime Pack 명칭 고정** (`codebook_runtime_pack`, legacy `codepack_recovery` 호환) 및 readiness 아티팩트 A 궤적 반영 (2026-04-09)
