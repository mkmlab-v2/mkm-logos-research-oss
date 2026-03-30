# NotebookLM 소스 매니페스트 (A/B 이원)

**작성일**: 2026-03-29  
**정의**: **A = Fact-Lock(팩트 고정)**, **B = Creative-Lock(통찰·가설)**. B는 본선 OOF·실매매 트리거와 A를 혼선 없이 적용.

**Vault 동기화**: `scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1`가 이 표를 `notebooklm_sources/`로 복사(SSOT 반영). 공유 Vault 루트는 환경의 `MKM_VAULT_ROOT` 또는 스크립트 `-VaultRoot`로 지정.

### Unified-Intelligence — 메인 지휘 (2026-03-29)

- **통합 전황판 (A1 16-State + Logos Phase 1 + Git 슬롯)**: `docs/final/UNIFIED_INTELLIGENCE_BATTLEBOARD_2026-03-29.md`
- **합류 방식**: 병렬 창은 **경로·커밋 해시·exit code**로만 보고 → 메인에서 매니페스트·전황판 갱신. **매니페스트 직접 편집은 메인 창만.**

---

## A 궤적 — **팩트** 소스 (Hard-Fact)

| 우선순위 | 경로 (워크스페이스 기준) | 비고 |
|----------|--------------------------|------|
| P0 | `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` | 헌법 추론 구현 SSOT |
| P0 | `docs/final/master_codebook_dual_track.template.json` | 듀얼 트랙 코드북 템플릿 |
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
| DSS / Qumran | `docs/final/DSS_APOCRYPHA_FRONTLINE_CLOSEOUT_2026-03-27.md` | Creative-Lock; frontline closeout SSOT |
| 명리·융합 의사결정 | `docs/final/MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json` | SSOT; B 노트북에는 동명 텍스트 소스로 반영(`MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json`). A와 역할 분리 |
| AI·명리·만세 외부 참조 | `docs/final/AI_MYEONGNI_MANSE_EXTERNAL_REFERENCE_LANDSCAPE_2026-03-29.md` | 타 서비스·RAG·LLM 패턴 정리(참고만); 본선 OOF·A와 무단 합선 금지 |
| AI-Logos 외부 연구 (arXiv·Kaggle) | `docs/external_research/AI-Logos_Research_Bibliography_2026.md` | B-only; **Confirmed URL** 서지·TBD 분리; 작전 **LeWorld-Enlightenment**; A·본선 자동 합선 금지 |
| Logos 교집합 랭킹 SSOT | `docs/final/LOGOS_INTERSECTION_RANKING_SSOT_2026-03-29.md` | `mean`/`min` 지표·경로; λ(편향)와 기호 분리; 본선·실매매 자동 합선 금지 |
| 한의 원전·프록시 | `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS_Myeongni_Ext.md` · `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §9 | 코퍼스 B 분리·승격 경계; 별도 handoff MD 미작성 시 본 문서가 SSOT |

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

## 작전지휘부(Ops) NotebookLM 메모 (2026-03-29)

- **NotebookLM**: 노트북명 `작전지휘부 Ops20260318`, ID `347e5cbe-0ade-4615-9aac-8747d4fa644e`, 소스 **151**개 (`notebook_get` 2026-03-29 재확인; §8·타 문서와 수치 불일치 시 본 행 우선). **2026-03-29**: 정규화 제목(앞뒤 공백·연속 공백 통일) 기준 **중복 소스 삭제** 완료(이전 **230**개 → **151**개; 동일 제목이 여러 개일 때 `sources` 순서상 **마지막 `source_id`만 유지**). `source_count`는 NotebookLM **현재 엔트리 수**이다.
- **전체 wipe**: **기본 금지**. 소스 대량 삭제는 사용자가 **명시적으로 재구축·전체 재업로드**를 요청한 경우에만 수행.
- **`OPS_ONEPAGE_STATUS_LATEST.md`**: 워크스페이스 `docs/final/OPS_ONEPAGE_STATUS_LATEST.md`는 **미존재**할 수 있음. NotebookLM에는 소스 **제목**으로만 존재할 수 있음. 새 MD 남발 대신 `docs/final/` 기존 SITREP·본 매니페스트에 **Gap 한 줄** 기록.
- **로컬 브리지 문서**: `docs/작전지휘부/` 등 경로는 **Vault·다른 머신에만** 있을 수 있음. `source_add` 전 **파일 존재 확인** 필수.

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

- **B — AI-Logos 번들**: ✅ `source_add`(URL 5 + file 서지) 반영·**`notebook_get` B=21** 확인(2026-03-29; Deep Past Kaggle URL 추가). ✅ 서지에 **arXiv 2407.12013(Enoch)**·**deeppast.org** Confirmed 반영(2026-03-29). ✅ Deep Past **Kaggle 대회 URL**: 서지 `AI-Logos_Research_Bibliography_2026.md` + **NotebookLM URL 소스** `f0cbb85f-b5bf-4ec5-b958-4c690d282a01` (`source_add`, 2026-03-29). ✅ **Operation [B] 장부**: 매니페스트에 B 노트 **21개 전체** `source_id`·`title` 실측 표 박제(2026-03-29).
- **B — `notebook_query` (노트 `af639d3e-b455-4f3f-8e25-47f58d962c60`)**: Q1/Q2 Gap 유지. ✅ **후속 적층 질의**(LeWM 초록 ↔ DSS 세그멘테이션·필적 식별 대조, 사실/가설 표·비유 한계) `conversation_id` **`deb0fc0c-5e20-4041-a917-0fe240f0b2bb`**로 실행·응답 수신(2026-03-29); 인용 소스 ID: `794cf83b-…`(LeWM), `f4a61719-…`(2411.10668), `0939abb4-…`(1QIsaa).
- **Logos BTC 공명**: canon-only **BULL/BEAR/SIDEWAYS FULL** 산출물은 본 매니페스트 Logos 표에 등록됨. **Ancient-expanded**(`--ancient-resonance`)는 별도 파일명으로 실행·등록(캐논 FULL 시리즈와 혼선 금지).
- **이제마 B**: Source-Boost·AI-Logos 번들·Deep Past Kaggle URL 반영·`notebook_get` B=21 확인 후 — 통찰 품질·중복 소스 점검, 필요 시 Vault `sync_notebooklm_sources_to_mkm_data_vault.ps1`. `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §9·B 표와 정합 유지.  
- **명리**: SSOT `MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json`는 B에 동기화됨; MD 스키마 초안은 `data/corpus/ijeoma/schemas/myeongni_fusion_schema_v2_draft.md`(B 노트 등록)와 `docs/final/myeongni_fusion_schema_v2_draft.md`(미러). 본선 OOF·실매매 트리거 자동 연동은 **헌법·팩트 문서에서 명시된 구현 경로가 있을 때만** — 스키마만으로 자동 합선하지 않음.
- **Master Probe (2026-03-29)**: ✅ 매니페스트 **A 궤적** 및 **§명리 16-State Master Probe**에 `data/myeongni/16_STATE_MASTER_PROBE_v1.json`·`data/myeongni/myeongni_16_state_experiment_20260329.jsonl` 경로·격벽·검증 질의 SSOT 박제. 차기(선택): 대상 노트북에 `source_add`(file)로 JSON 주입 후 본문 §검증 질의로 권위 응답 확인.

---

**상태**: A 궤적 · Logos-Insight 표(wide_20 JSON/CSV 포함) · **BTC 레짐 공명 FULL JSON 3종·btc_regime_map** 매니페스트 반영 · 이제마 B 분리 · 작전지휘부 151 소스·wipe 정책 · 만세력·사주 A/B `notebook_get` 검증 완료(표 ID 일치; **B 소스 21개**·파일 7·arXiv 3·Kaggle 3·위키 8·AI-Logos 서지·명리 스키마·외부 참조 랜드스케이프·Deep Past Kaggle URL) · **B `notebook_query`** 소스-바운드 Q1/Q2 Gap 기록(2026-03-29) · **DSS Fusion** 노트(`2b2eeff1-…`) 소스 8개 검증 · OPS_ONEPAGE Gap 기록 정책 · **Master Probe v1 / 16-State 정본(2026-03-29) 매니페스트 SSOT** (2026-03-29)
