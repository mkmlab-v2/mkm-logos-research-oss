# Logos · 원어 아톰 GraphRAG 브릿지 v1

**상태:** `[HYPO]` · `research_only` · `[NON_GATING]` — **미구현 완성품 아님**.  
**Fact-Lock:** 경로·통과는 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 및 `.py`·pytest·아티팩트만.  
**상위 맵:** `LOGOS_SYMBOLIC_INTERPRETATION_LAYER_MAP_V1.md` · 연대 blind **4.3%**(`text_blind`)는 **era 매칭 한계**이며 본 브릿지로 대체 주장하지 않음.

---

## 0. 정의 (환각 경계)

| 말해도 되는 것 | 말하면 안 되는 것 |
|----------------|------------------|
| 현대 개념 → **기능 노드** → 성경 **절/원어 앵커**까지 **감사 가능한 경로** | “성경이 반도체를 예언했다” |
| **Semantic tracking** · topology path · B-track 쇼룸 해설 | 예언 적중 · Track A · 실매매 트리거 |
| PoC: path JSON + `honest_metrics` (Wire) | **% 동형·적중** without eval artifact |

---

## 1. 3단 아키텍처 (목표)

```
[현대 query: e.g. 반도체]
        │
        ▼
[L2 concept_bridge nodes]  ← LLM/규칙 해체 (HYPO, human_review 권장)
        │
        ▼
[L1 lemma/atom nodes]      ← build_original_language_master_atoms (heuristic lemma)
        │
        ▼
[L0 verse nodes]           ← corpus graph / aramaic::Book.ch.v
```

**GraphRAG:** `run_logos_graph_seed_chain_v1.py`(BFS) · `run_graphrag_pilot_router_v1.py`(글로벌 아톰망) · **`run_logos_subgraph_graphrag_router_v1.py`**(성경 서브그래프·concept_bridge).

---

## 2. 레포 FACT vs GAP (2026-05-22)

| 층 | FACT (디스크·스크립트) | GAP |
|----|----------------------|-----|
| 연대·Field | `logos_chronology_*` · `apply_logos_chronology_to_graph_v1.py` | ≠ lemma GraphRAG |
| 코퍼스·그래프 | `build_logos_corpus_graph_bundle_v1.py` · `bible_meaning_graph_*.jsonl` | `CONTAIN` lemma↔verse 스키마·대량 엣지 |
| 원어 아톰 | `scripts/core/build_original_language_master_atoms.py` | Strong’s/TBESH급 lemma SSOT |
| 시드·BFS | `run_logos_graph_seed_chain_v1.py` | 현대 개념 시드 입력 표준 |
| Wire PoC | `build_mkm_graph_wire_rag_poc_v1.py` · `honest_metrics` | 브릿지→wire 자동 체인 |
| 글로벌 GraphRAG | `run_graphrag_pilot_router_v1.py` | 성경 서브그래프 전용 |
| **Phase 0** | `build_logos_concept_bridge_semiconductor_poc_v1.py` → `logos_concept_bridge_semiconductor_poc_v1_latest.json` | 1 query 고정·수치 없음 |

---

## 3. Phase 로드맵

| Phase | 산출 | 게이트 |
|-------|------|--------|
| **0** (now) | 반도체 정적 bridge JSON + seed chain 연동 스모크 | pytest schema · no % claims |
| **1** | `logos_lemma_verse_edges_v1` 빌더 + manifest | corpus split test |
| **2** | concept_bridge LLM layer + `human_reviewed` ratio | governance warning if 0 human |
| **3** | subgraph router + 쇼룸 v6 audit panel | NON_GATING · MS 4.3% only for era |

---

## 4. Phase 0 예시 경로 (고정 템플릿, not scored)

- `concept:semiconductor` → `function:refined_silica` → `lemma:hebrew:זכוך` proxy → `verse:Job.28.17` (정제 유리 은유)
- → `function:light_etching` → `lemma:hebrew:פתח` proxy → `verse:Zech.3.9`
- → `function:iron_clay_mix` → `lemma:aramaic:ערב` proxy → `verse:Dan.2.43`

**주의:** lemma 라벨은 **교육용 앵커 문자열**이며 morphology 검증 전.

---

## 5. 원클릭

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-LogosOlGraphBridgeParallel_v1.ps1
```

---

## 6. MS / 대외

- **방어선 유지:** `reports/ms_fact_lock_brief_3layer_v1.md` — 역사 `text_blind` **4.3%** only.
- 본 브릿지: Track C·B2B 부록 **“semantic path demo”** 슬롯만 — 법무 sign-off 전 send 금지.

**CDIM (병렬):** `LOGOS_CROSS_DOMAIN_INTERFACE_MAPPER_V1.md` — lemma/verse GraphRAG와 **코퍼스 오염 없이** 렌즈 융합만 중계.
