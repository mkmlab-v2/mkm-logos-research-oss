# Logos · 크로스 도메인 인터페이스 매퍼 v1

**상태:** `[HYPO]` · `research_only` · `[NON_GATING]` — **본선·실매매·Track A 자동 트리거 아님**.  
**Fact-Lock:** 구현·통과·수치는 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 및 호출 가능 `.py`·pytest·exit code·아티팩트만. 본 문서는 **격벽·배선·금지** 설계 SSOT이며 “이미 완성 배포됨”을 의미하지 않는다.  
**상위:** `MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md` §1.0.5(3+1·Field) · `MKM_TRINITY_INDEX_V1.json` · `AGENTS.md` 「렌즈 역할 계약」  
**인접 브릿지:** `LOGOS_ORIGINAL_LANGUAGE_GRAPH_RAG_BRIDGE_V1.md` (lemma/verse GraphRAG, 오행 무관) · `LOGOS_INTERSECTION_RANKING_SSOT_2026-03-29.md` (4D join `[HYPO]`)

---

## 0. 한 줄 정의

**Cross-Domain Interface Mapper (CDIM)** = 서로 다른 코퍼스·엔진의 **독립 산출물**만 읽고, **타입드 관계·정합 스냅샷**으로 중계하는 **최상위 비오염 레이어**이다.  
성경 텍스트·verse 인덱스·GraphRAG 노드에 **음양오행(목·화·토·금·수) Universal Taxonomy를 이식하지 않는다.**

---

## 1. 설계 원칙 (격벽 전제)

| 원칙 | 내용 |
|------|------|
| **P1 — 코퍼스 순수성** | Logos 코퍼스는 `verse_id`·원어 atom·4D medoid·era chronology·`evidence_refs`만 SSOT. **verse-level `ohaeng` / `yin_yang` 태그 금지.** |
| **P2 — 렌즈 독립 실행** | 명리·사상·Logos는 각각 `run_lens_*` → `*_independent_lens_latest.json`. 한 렌즈 실패를 다른 렌즈로 **메우지 않음.** |
| **P3 — Field 주·2차 보** | 1차 Field = `regime_map` 실물 **주**. 2차 성경·명리 서사 = **보** · **실전 트리거 금지** (`.cursor/rules/regime-field-constitution.mdc`). |
| **P4 — 중간 좌표계** | 크로스 도메인 연결은 **공유 온톨로지 병합**이 아니라 **4D 벡터·typed edge·fusion stub·concept path** 등 **감사 가능한 중간 표현**만 허용. |
| **P5 — 수치·승격** | CDIM은 **% 동형·적중·예언 품질**을 산출하지 않는다. MS 방어선: era `text_blind` **4.3%** only (`reports/ms_fact_lock_brief_3layer_v1.md`). hardset/heuristic/78.7% **MS·Track A 인용 금지.** |
| **P6 — 출력 고정** | 보고 순서: **`Field` → `Lens(사상/명리/성경)` → `Conflict` → `Final Action(HOLD/REDUCE/WATCH)`** — Logos 렌즈는 **`[NON_GATING]`** 유지. |

---

## 2. 금지·허용 (환각·오염 방지)

### 2.1 NEVER (데이터 DNA 오염)

- 성경 31,102절(또는 `verse_4pipeline`·`bible_meaning_graph`)에 **오행·음양 단일 라벨** 일괄 인젝션 (LLM 자동·수동 모두).
- GraphRAG에서 **`node:火`** 하나로 “성령의 불”과 “명리 午火”를 **동일 노드**로 합선.
- `4d_to_ohaeng_*` 파이프라인 이름을 **“성경도 오행으로 분류했다”**는 근거로 서술 (`CONSTITUTION` §302–303: **레짐 오버레이 라벨**, 전통 1:1 단정 아님).
- CDIM 산출을 **Track A·live trading·regime_map 트리거**에 자동 연결.
- **topology_overlap %·RAG 100%·blend 91.7%** 등 채팅·브리핑 수치를 디스크 SSOT 없이 대외·MS에 사용.

### 2.2 ALLOWED (타입드 중계만)

| 중계 유형 | 설명 | 레포 FACT 포인터 |
|-----------|------|------------------|
| **Lens fusion stub** | 3~4 렌즈 `direction_score`·`conflict_summary`·Logos `evidence_refs` | `report_independent_lens_fusion_stub_v0.py` → `independent_lens_fusion_stub_latest.json` |
| **Cross-lens RAG fusion** | 위 스텁 + 독립 렌즈 스냅샷 → JSON/MD | `build_cross_lens_rag_fusion_v1.py` → `cross_lens_rag_fusion_latest.json` |
| **4D assignment join** | Logos 상위 구절 ↔ 명리 16상 `vector_4d` 코사인 배정 | `join_logos_verses_myeongni_states_4d.py` · `[HYPO]` · `LOGOS_STATE_MAPPING_V1.json` |
| **Verse 4D projection** | 구절 → 코드북 atom (오행 라벨 아님) | `project_logos_verse_4d_to_lexicon_v1.py` · `verse_4pipeline` 체인 |
| **Graph confirm edge** | 렌즈 간 동일 앵커 “확인” (오행 taxonomy 아님) | `cross_lens_confirm` · `aramaic_graph_edge_v1` |
| **Concept bridge path** | 현대 개념 → function → lemma proxy → verse | `LOGOS_ORIGINAL_LANGUAGE_GRAPH_RAG_BRIDGE_V1.md` · `logos_concept_bridge_*` |
| **명리 quant block** | 출생/세션 엔진 **내부** 오행 질량 (`myeongni_b_track_quant_block_v0`) | `run_lens_myeongni.py` — **Logos 인덱스와 분리** |
| **임상 교차검증** | 명리 가시 오행 vs 사상 체질 **표면만** | `patient_intake_myeongni_sasang_cross_v1.py` — 성경 미합선 |

---

## 3. 아키텍처 (목표 배선)

```
                    ┌─────────────────────────────────────┐
                    │  Field (1차 regime_map · 실물)       │
                    │  [주] — 트리거·가중은 운영 게이트      │
                    └─────────────────┬───────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          │                           │                           │
          ▼                           ▼                           ▼
   ┌──────────────┐           ┌──────────────┐           ┌──────────────┐
   │ Lens: 명리    │           │ Lens: 사상    │           │ Lens: Logos   │
   │ run_lens_     │           │ run_lens_     │           │ run_lens_     │
   │ myeongni      │           │ sasang        │           │ logos         │
   │ (오행 연산은   │           │ (체질·축만)   │           │ (4D·verse·    │
   │  렌즈 JSON    │           │               │           │  era·RAG)     │
   │  내부만)      │           │               │           │               │
   └──────┬───────┘           └──────┬───────┘           └──────┬───────┘
          │                           │                           │
          └───────────────────────────┼───────────────────────────┘
                                      ▼
                    ┌─────────────────────────────────────┐
                    │  CDIM — Cross-Domain Interface       │
                    │  · fusion_stub / cross_lens_rag      │
                    │  · optional: 4d_join [HYPO]          │
                    │  · optional: concept_bridge path     │
                    │  · typed: align | conflict | ref_only │
                    └─────────────────┬───────────────────┘
                                      ▼
                    ┌─────────────────────────────────────┐
                    │  Conflict Resolver (템플릿·비-LLM)   │
                    │  + human_commander_gate (시장/Track B)│
                    └─────────────────┬───────────────────┘
                                      ▼
                         Final Action (운영 게이트 확정)
                         [NON_GATING] Logos 단독 → 주문 없음
```

**CDIM은 “새 추론 엔진”이 아니라** 기존 `independent_lens_fusion_stub` + `build_cross_lens_rag_fusion` + (선택) join/bridge 산출을 **한 계약·한 MD/JSON 슬롯**으로 묶는 **인터페이스 가이드**이다.

---

## 4. CDIM 산출 계약 (초안 · 스키마 TBD)

Phase 0는 **기존 JSON 조합**만; 신규 스키마는 Phase 1에서 `docs/final/schemas/logos_cross_domain_interface_v1.schema.json` 로 고정 예정.

### 4.1 필수 입력 (read-only)

| `input_id` | 기본 경로 | 렌즈 |
|------------|-----------|------|
| `myeongni_lens` | `docs/final/artifacts/myeongni_independent_lens_latest.json` | 명리 |
| `sasang_lens` | `docs/final/artifacts/sasang_independent_lens_latest.json` | 사상 |
| `logos_lens` | `docs/final/artifacts/logos_independent_lens_latest.json` | Logos |
| `fusion_stub` | `docs/final/artifacts/independent_lens_fusion_stub_latest.json` | 융합 |

### 4.2 선택 입력 (`[HYPO]`)

| `input_id` | 기본 경로 | 용도 |
|------------|-----------|------|
| `cross_lens_rag` | `docs/final/artifacts/cross_lens_rag_fusion_latest.json` | RAG·ANN 쿼리 스냅샷 포함 대시보드 |
| `logos_state_mapping` | `docs/final/artifacts/LOGOS_STATE_MAPPING_V1.json` | 4D join 배정 증거 |
| `concept_bridge` | `docs/final/artifacts/logos_concept_bridge_*_latest.json` | 현대 개념→verse path demo |
| `market_myeongni` | `docs/final/artifacts/market_myeongni_lens_latest.json` | 시장 오버레이 (명리 상류) |
| `market_sasang` | `docs/final/artifacts/market_sasang_lens_latest.json` | 시장 사상 (비의료) |

### 4.3 CDIM 출력 필드 (논리)

```json
{
  "schema": "logos_cross_domain_interface_v1",
  "labels": ["HYPO", "NON_GATING", "research_only"],
  "field_regime_id": "<from regime_map or observational stub>",
  "lens_snapshots": [ "... paths + direction_sign only ..." ],
  "cross_refs": [
    {
      "relation_type": "align|conflict|ref_only|4d_cosine_assign|concept_path",
      "from_domain": "myeongni|sasang|logos|market",
      "to_domain": "logos|myeongni|...",
      "evidence_path": "<repo-relative artifact>",
      "verse_ids": ["optional"],
      "note": "no merged ontology; no ohaeng on verse index"
    }
  ],
  "conflict_summary": "<from fusion_stub, verbatim policy>",
  "forbidden_claims": [
    "universal_ohaeng_taxonomy_on_bible_corpus",
    "logos_gating_live_trade",
    "ms_era_metrics_other_than_text_blind_4_3pct"
  ]
}
```

**`relation_type` 고정어휘** — GraphRAG 엣지·융합 스텁과 **이름만 정렬**; 의미 병합 금지:

| `relation_type` | 의미 |
|-----------------|------|
| `align` | 방향 부호·다수결 일치 (fusion `consensus`) |
| `conflict` | 소수 렌즈·`conflict_summary` |
| `ref_only` | Logos `evidence_refs` 인용만, 명리/사상 점수에 **가산 없음** |
| `4d_cosine_assign` | `join_logos_verses_myeongni_states_4d` 배정 행 |
| `concept_path` | `concept_bridge` L2→L0 경로 (예언 아님) |

---

## 5. 레포 역사 맵 (Universal Taxonomy vs 실제 작업)

| 지휘관 우려 | 레포 실제 | CDIM 판정 |
|-------------|-----------|-----------|
| 음양오행으로 성경+동양 **한 인덱스** | **미구현** (FACT 없음) | **금지 유지** |
| 오행으로 **그래프 밀도↑** | `cross_lens_confirm`·fusion·4D join | **허용** — 오행 노드가 아닌 **typed ref** |
| `4d_to_ohaeng` | 레짐·예언 오버레이 B-track | **CDIM 입력에서 Logos 코퍼스와 분리** |
| 명리 오행 질량 | `myeongni_b_track_quant_block_v0` | **명리 렌즈 JSON 내부만** |
| 철학 RAG + fusion | `philosophy_lane_rag_pilot_v1.py` `--invoke-cross-lens-fusion` | **CDIM 동일 패턴** (Track B) |

---

## 6. Phase 로드맵

| Phase | 목표 | 산출 | 게이트 |
|-------|------|------|--------|
| **0** (now) | 문서·배선 + read-only assemble | 본 MD · `assemble_logos_cross_domain_interface_v1.py` · `Run-LogosCrossDomainInterfaceParallel_v1.ps1` | `tests/test_logos_cross_domain_interface_v1.py` |
| **1** | (same) — optional 쇼룸·digest MD emitter | `logos_cross_domain_interface_latest.json` | jsonschema `--validate` |
| **2** | 쇼룸·Track C 대시보드에 **NON_GATING** 패널 1칸 (`build_mkm_trackc_ops_dashboard_v1` 확장) | 패널 `trackc.cross_domain_interface` | PUBLIC_FACING 체크리스트 |
| **3** | GraphRAG bridge Phase 1+ (`lemma↔verse`) 와 **병렬** — CDIM은 여전히 **verse에 ohaeng 없음** | `LOGOS_ORIGINAL_LANGUAGE_GRAPH_RAG_BRIDGE_V1` §연동 | era 4.3% only in MS |

**Phase 0 원클릭 (기존, CDIM ≡ 동일 의미):**

```powershell
# 1) 독립 렌즈 (이미 있으면 생략 가능)
py scripts/run_lens_myeongni.py
py scripts/run_lens_sasang.py
py scripts/run_lens_logos.py

# 2) 융합 스텁 + cross-lens RAG
py scripts/report_independent_lens_fusion_stub_v0.py
py scripts/build_cross_lens_rag_fusion_v1.py

# 3) [HYPO] 4D join · concept bridge (선택)
py scripts/join_logos_verses_myeongni_states_4d.py
py scripts/build_logos_concept_bridge_semiconductor_poc_v1.py
```

---

## 7. MS · Oracle · 대외

| 채널 | 허용 | 금지 |
|------|------|------|
| **MS / 국방 Fact-Lock** | era `text_blind` **4.3%**; “렌즈 격벽·CDIM은 관측·해설” 한 줄 | hardset 92.6%/100%, gold_tags 78.7%, RAG %, Universal 오행 매핑 주장 |
| **Track C / B2B** | “독립 렌즈 → 정합 패널” 데모 · `concept_path` 샘플 | “성경이 ○○ 산업 예언” · 법무 sign-off 전 send |
| **쇼룸** | `cross_lens_rag_fusion_latest.md` 링크 | 오행 라벨이 붙은 verse 검색 UI |
| **MISSION_LOG Oracle** | CDIM Phase·다음 스크립트 1줄 | Phase 표 장문 |

---

## 8. CONSTITUTION · P0 연동 (다음 편집 시)

본 설계 반영 시 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §3 Logos 표에 **한 행** 추가 권장:

- **CDIM v1 [HYPO]** · `LOGOS_CROSS_DOMAIN_INTERFACE_MAPPER_V1.md` · assemble 스크립트(Phase 1) · A-track·실매매 자동 합선 금지

`scripts/verify_p0_constitution_gate_paths.ps1` — Phase 1 이후 산출 경로 등록.

---

## 9. 교차 참조

| 문서 | 역할 |
|------|------|
| `LOGOS_ORIGINAL_LANGUAGE_GRAPH_RAG_BRIDGE_V1.md` | lemma/verse; CDIM과 **병렬**, 코퍼스 오염 없음 |
| `LOGOS_INTERSECTION_RANKING_SSOT_2026-03-29.md` | 4D join · ANN · `[HYPO]` |
| `INDEPENDENT_LENS_FUSION_STUB_V0_CONTRACT.json` | conflict 템플릿 SSOT |
| `PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` | 대외 수사 상한 |
| `reports/ms_fact_lock_brief_3layer_v1.md` | MS 수치 방어선 |

---

**문서 버전:** v1.0.0 · **2026-05-22** · `[HYPO]` 초안 — 지휘관 결선 지침 반영.
