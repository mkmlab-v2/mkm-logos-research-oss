# NotebookLM 소스 매니페스트 (A/B 이원)

**작성일**: 2026-03-29  
**정의**: **A = Fact-Lock(팩트 고정)**, **B = Creative-Lock(통찰·가설)**. B는 본선 OOF·실매매 트리거와 A를 혼선 없이 적용.

**Vault 동기화**: `scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1`가 이 표를 `notebooklm_sources/`로 복사(SSOT 반영). 공유 Vault 루트는 환경의 `MKM_VAULT_ROOT` 또는 스크립트 `-VaultRoot`로 지정.

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

**확인**: Vault·로컬 경로 정합은 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §6 참조.

---

## B 궤적 — **통찰** 소스 (Insight / Hypothesis)

| 항목 | 경로 (또는 TBD) | 비고 |
|------|------------------|------|
| DSS / Qumran | `docs/final/DSS_APOCRYPHA_FRONTLINE_CLOSEOUT_2026-03-27.md` | Creative-Lock; frontline closeout SSOT |
| 명리·융합 의사결정 | `docs/final/MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json` | SSOT; B 노트북에는 동명 텍스트 소스로 반영(`MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json`). A와 역할 분리 |
| AI·명리·만세 외부 참조 | `docs/final/AI_MYEONGNI_MANSE_EXTERNAL_REFERENCE_LANDSCAPE_2026-03-29.md` | 타 서비스·RAG·LLM 패턴 정리(참고만); 본선 OOF·A와 무단 합선 금지 |
| 한의 원전·프록시 | *(별도 자료)* | 코퍼스 B — `KOREAN_MEDICAL_CANON_INGEST_HANDOFF_2026-03-28.md` 준수 |

---

## 이제마_B_Track (분리 원칙)

**원칙**: 라벨 코호트 **A**와 원전·프록시 코퍼스 **B**를 분리. **B를 본선 OOF에 자동 합선하지 않음.**

**인벤토리 기준일**: 2026-03-29 (`data/corpus/ijeoma/_inventory` 등).

### B용 소스 (NotebookLM·Vault 동기화 시)

| 경로 | 비고 |
|------|------|
| `data/corpus/ijeoma/originals/jeokcheonsu_core_logic_chunk.md` | Source-Boost: 적천수 맥락·일간 강약 스캐폴드(B·OOF 비합선); **Pending Ingest** → 반영 후 제거 |
| `data/corpus/ijeoma/schemas/myeongni_fusion_schema_v2_draft.md` | Source-Boost: MYEONGNI 융합 JSON 스키마 MD 설명(v2 DRAFT 표시); **Pending Ingest** → 반영 후 제거 |
| `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS_Myeongni_Ext.md` | Source-Boost: B 전용 추론 경계(본 FACTS § 포인터); **Pending Ingest** → 반영 후 제거 |
| `data/corpus/ijeoma/_inventory/IJEOMA_NOTEBOOKLM_QUERY_SET_2026-03-29.md` | 쿼리 세트 |
| `data/corpus/ijeoma/_inventory/IJEOMA_INSIGHT_UNITS_XINGMING_SAMPLE_2026-03-29.json` | 통찰 단위 샘플(JSON) |
| `data/corpus/ijeoma/_inventory/IJEOMA_INSIGHT_UNITS_SASANG_FOUR_SAMPLE_2026-03-29.json` | 사상 사본 샘플(JSON) |
| `data/corpus/ijeoma/_inventory/IJEOMA_CODEBOOK_INDEX_DRAFT_2026-03-29.json` | 코드북 인덱스 초안 |
| `data/corpus/ijeoma/e_drive_mirror/donguisusebowon_mastery_report.md` | 동의보감 마스터리 보고서(NotebookLM 소스) |
| `data/corpus/ijeoma/originals/jeokcheonsu_core_logic_chunk.md` | 《적천수》맥락 일간 강약 판별 **운영 추출**(B; 원문 전문 비대체) |
| `docs/final/myeongni_fusion_schema_v2_draft.md` | `MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json` 사람 읽는 초안(NotebookLM) |
| `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` | §8 A/B 분리·구현 팩트 SSOT; 이제마 B 노트북 그라운딩(환각 방지·행동 근거) |

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

- **NotebookLM**: 노트북명 `작전지휘부 Ops20260318`, ID `347e5cbe-0ade-4615-9aac-8747d4fa644e`, 소스 **229**개 (`notebook_get` 2026-03-29; §8·타 문서와 수치 불일치 시 본 행 우선).
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

**MCP 검증 (2026-03-29, 현재 계정)**: `notebook_get` 성공 — A 제목 `만세력·사주_AI_A_제품 (MKM Fact-Lock)`, 소스 7개; B 제목 `만세력·사주_AI_B_연구 (MKM Abstract)`, 소스 **11**개(파일 소스 3 + Wikipedia URL 8; `source_add` 일괄 반영). **B 파일 소스 확장 목표(2026-03-29)**: 아래 2개를 `source_add`하면 **파일 5개 + URL 8 = 총 13** (워크스페이스 반영 후 `notebook_get`으로 재확인).

**클라우드 소스 제목 (실측, `notebook_get`과 동일)** — 카운트 A=7·B=11(파일 3 + URL 8); **+2 파일 추가 시** B=13:

| 노트북 | 소스 제목 (표시명) |
|--------|-------------------|
| A | `ATHENA_MANSE_SAJU_NOTEBOOKLM_SEED_2026-03-29.md` |
| A | `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` |
| A | `FACT_LOCK_BRIEF_2026-03-27.md` |
| A | `MANSEYEOK_E2E_CHECKLIST.md` |
| A | `MANSE_SAJU_AI_PRODUCT_PATH_MAP_2026-03-29.md` |
| A | `MKMLIFE_LLM_ROUTING_OVERVIEW.md` |
| A | `OPERATIONS_SSOT.md` |
| B | `MANSE_SAJU_AI_RESEARCH_SYNTHESIS_2026-03-29.md` |
| B | `MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json` |
| B | `AI_MYEONGNI_MANSE_EXTERNAL_REFERENCE_LANDSCAPE_2026-03-29.md` |
| B | *(Wikipedia)* Four Pillars of Destiny |
| B | *(Wikipedia)* Korean calendar |
| B | *(Wikipedia)* Sexagenary cycle |
| B | *(Wikipedia)* Lunisolar calendar |
| B | *(Wikipedia)* Chinese calendar |
| B | *(Wikipedia)* 사주 |
| B | *(Wikipedia)* 만세력 |
| B | *(Wikipedia)* 사주명리학 |
| B | *(워크스페이스 반영 후 `source_add` 예정)* `jeokcheonsu_core_logic_chunk.md` |
| B | *(워크스페이스 반영 후 `source_add` 예정)* `myeongni_fusion_schema_v2_draft.md` |

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

**명리 스키마 B 반영 (2026-03-29)**: SSOT는 `docs/final/MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json`. 파일 소스 `source_add`가 실패한 경우 **`source_type: text`**로 본문 전체 업로드 가능 — B에 `MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json` 제목으로 등록됨(`source_id` `77ae458c-259f-4e92-ad12-ae5e2bd650f8`). 구현·경로 팩트는 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §6과 정합 유지.

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

**원시 코퍼스** (`data/logos/manuscripts/*.jsonl`)는 노트에 직접 붙이기 어려울 수 있음 → 필요 시 **MD/TXT 청크** 또는 **PDF**로 내보낸 뒤 `source_add file`.

---

## 차기 작업 (Gap)

- **이제마 B**: 위 표 + `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §8.  
- **명리**: SSOT `MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json`는 B에 동기화됨. 본선 OOF·실매매 트리거 자동 연동은 **헌법·팩트 문서에서 명시된 구현 경로가 있을 때만** — 스키마만으로 자동 합선하지 않음.

---

**상태**: A 궤적 · Logos-Insight 표(wide_20 JSON/CSV 포함) · 이제마 B 분리 · 작전지휘부 229 소스·wipe 정책 · 만세력·사주 A/B `notebook_get` 검증 완료(표 ID 일치; B 소스 11개=파일 3+위키 8·명리 스키마·외부 참조 랜드스케이프·Wikipedia `source_add` 반영) · **DSS Fusion** 노트(`2b2eeff1-…`) 소스 8개 검증 · OPS_ONEPAGE Gap 기록 정책 (2026-03-29)
