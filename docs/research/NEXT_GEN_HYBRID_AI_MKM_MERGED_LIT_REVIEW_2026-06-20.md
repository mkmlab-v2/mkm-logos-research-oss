# 차세대 하이브리드 AI 구현 — MKM 병합 리뷰 (Tier 0→1) [HYPO]

**Merged:** 2026-06-20 · **Skill:** mkm-deep-research v1.1 Tier 0→1  
**Inputs:**

| Tier | File | Role |
|------|------|------|
| **0x** | `docs/research/raw/universal_root_lexicon_matrix_gemini_report_2026-06-21.md` | Incremental raw drop (2026-06-22) |
| **0x** | `docs/research/raw/universal_root_lexicon_matrix_gemini_prompt_v1.md` | Incremental raw drop (2026-06-22) |
| **0x** | `docs/research/raw/universal_root_lexicon_matrix_cursor_sweep_2026-06-21.md` | Incremental raw drop (2026-06-22) |
| **0x** | `docs/research/raw/notion_sandbox_usage_checklist_v1.md` | Incremental raw drop (2026-06-22) |
| **0x** | `docs/research/raw/cloudflare_dns_weekly_token_scope_v1.md` | Incremental raw drop (2026-06-22) |
| **0a** | `docs/research/raw/tier0_hybrid_ai_web_sweep_2026-06-20.md` | Extended web/Exa forest (8 rounds) |
| **0b** | `docs/research/raw/delegation_hcm_4vault_moat_deep_sweep_2026-06-20.md` | Cursor delegation sweep (32 sources) |
| **0c** | `docs/research/raw/gemini_hcm_4vault_monetization_2026-06-20.md` | Gemini Deep Research supplement (**filter Part X**) |
| **1** | `docs/research/NEXT_GEN_HYBRID_AI_MKM_THEORY_IMPLEMENTATION_LIT_REVIEW_2026-06-20.md` | MKM Fact-Lock + digests + bench |
| **1b** | `docs/research/DELEGATION_HCM_4VAULT_MOAT_LIT_REVIEW_2026-06-20.md` | Delegation synthesis + monetization reality |

**Track:** B-track · `research_only` · `send_gate: HOLD`  
**Stats:** **~47 papers/systems** (incremental re-merge 2026-06-22)

> **Note:** Tier 0c = Commander Gemini paste ingested 2026-06-20. **Never** paste Gemini prose into README without Part X filter.

---

## Merge executive summary

**What the field agrees on (Tier 0 + papers):**

1. **Context windows alone do not solve long-horizon agents** — hierarchical / graph / OS-style memory is the 2025–26 consensus (6+ surveys in 6 months).
2. **Edge SLM + cloud LLM** is the default deployment pattern; research optimizes **routing, partition, or speculative verify** — not “cloud only.”
3. **Routing saves money** when done well, but **Oracle gap remains large**; many learned and commercial routers **fail vs Best Single** on LLMRouterBench.
4. **Agent-native memory** (ByteRover) and **file-tree wikis** challenge pure vector-RAG — aligns with MKM `llm_wiki/` direction.
5. **OSS + MCP** is a new secret-leak surface; EU CRA/PLD reward **non-commercial research OSS** positioning but **do not** make disclaimers a legal shield.

**What MKM can claim (Tier 1 Fact-Lock only):**

| Claim | Evidence |
|-------|----------|
| Shallow lane inject ~99.6% vs naive paste | `run_mkm_ltm_orchestration_bench_bundle_v1.py` |
| Orchestrated path ~33% vs naive | same |
| Gold router 12/12 CPU | `logos_gold_query_eval_v1_latest.json` |
| Cap×gold → baseline_production only | gold regression artifact |
| MIT OSS stack + send_gate scope | `mkm_solo_oss_release_policy_v1_latest.json` |
| Shallow router golden 16/16 live | `Run-OllamaShallowHybridReproduceBundle_v1.ps1` |
| Federated catalog + Vault2 pointers | `build_mkm_knowledge_catalog_v1.py` · `mkm_reference_pointer_registry_v1.json` |

### MKM 4-Vault Knowledge OS (repo status 2026-06-20 FACT)

| Vault | Role | SSOT path | Merge rule |
|-------|------|-----------|------------|
| **1 Governance LTM** | ops pins, must_keep, 72 concepts | `storage/meta/mkm_ops_memory_index_v1.json` · `mkm_long_term_memory_graph_v1.json` | anchor+overlay only |
| **2 Reference cold** | external doc pointers, no body ingest | `storage/meta/mkm_reference_pointer_registry_v1.json` | `inject_policy: on_demand_only` |
| **3 Shallow τ** | resume pack, `@docs` session surface | `docs/final/artifacts/mkm_chat_resume_pack_latest.md` | hard token budget |
| **4 Query RAG** | wiki raw, NL sidecar | `memory/obsidian_vault/llm_wiki/raw/` | B-track · not ops merge |

**This merged doc** is registered as `ref:research:nextgen_hybrid_merged` in Vault 2 and cross-linked in `docs/final/artifacts/mkm_knowledge_catalog_v1_latest.json` (`research_ssot`). Ollama shallow router emits **routing JSON hints** only — not bulk doc ingest into Vault 1.

**What MKM must NOT claim (Tier 0 filtered out):**

- DMF / 242× / LLMLingua multiples as product KPI  
- NSGA-II scheduler “shipped”  
- RET as routing quality metric  
- HCM as single ISO standard  
- EU disclaimer = full liability immunity  

---

## Part I — Narrative: Memory OS & hierarchical context (Plane 2)

### I.1 Field arc: from MemGPT to agent-native trees

**MemGPT (2310.08560)** established the metaphor: LLM context = RAM, external stores = disk, **agent function-calls page** content in/out. This is the intellectual ancestor of every “Memory OS” pitch in 2025–26.

**2024–25 systems** diversified storage:

- **Vector flat** — MemoryBank, Mem0  
- **Graph** — Zep, HippoRAG, GraphRAG, MAGMA  
- **Tree** — MemTree (ICLR 2025), RAPTOR  
- **Hierarchical tiers** — MemoryOS (STM/MTM/LPM), H-MEM (index layers)  

**2026 frontier — agent-native curation:**

- **ByteRover (2604.01599):** Same LLM that reasons **also curates** a Domain>Topic>Subtopic>Entry markdown tree with **AKL lifecycle** (draft→validated→core). 5-tier retrieval: most queries **<100ms without LLM**. SOTA on LoCoMo; competitive LongMemEval-S **without vector DB**.

**MKM alignment:** `memory/obsidian_vault/llm_wiki/raw→wiki` + LTM graph ≈ **dual stack** (ByteRover tree + Logos graph RAG). Differentiator: **lens 격벽** + B-track guards — not in academic benchmarks.

### I.2 Survey consensus (Tier 0 merge)

Six major surveys (2603.07670, 2602.05665, 2602.19320, 2602.06052, 2605.06716, 2603.21564) converge on:

| Theme | Implication for MKM |
|-------|---------------------|
| Hybrid stores win | Shallow pins + deep RAG + wiki — **correct direction** |
| Benchmark saturation | LoCoMo fits in 128K — need **agentic** tests (MemoryAgentBench) |
| Metric misalignment | F1 ≠ semantic correctness — use **gold CPU eval** + LLM-judge cautiously |
| Selective forgetting unsolved | ops pin eviction policy = `[Needs experiment]` |
| Graph vs tree tradeoff | Graph = multi-hop; tree = narrative flow — MKM uses **both** |

**Formal theory (2603.21564):** Maps systems to **segmentation α, consolidation C, reconstruction τ**. MKM shallow inject ≈ **τ with hard budget**; insight caps ≈ **C**.

### I.3 Context folding cluster

| System | Mechanism | MKM hook |
|--------|-----------|----------|
| HiAgent ACL 2025 | Subgoal memory chunks | MISSION_LOG next-1-action |
| AgentFold 2510.24699 | Granular vs deep consolidation | insight cap ablation |
| Cat / SWE-Compressor 2512.22087 | Learned fold at stage boundaries | Cursor session SLO |
| Theory paper 2603.21564 | StackPlanner, AgeMem tool actions | `[HYPO]` |

**Measured tension (MKM):** ultra_min cap **~56% smaller JSON** but **gold 5/12 regression** — same fidelity/size tradeoff AgentFold papers describe.

---

## Part II — Narrative: Edge–cloud & hybrid inference (Plane 1)

### II.1 Deployment taxonomy (survey 2507.16731)

1. **Separate models** — edge SLM + cloud LLM (MKM Ollama + Cursor)  
2. **Split model** — layer partition (Splitwise, CE-CoLLM)  
3. **Cascade** — try cheap first (FrugalGPT, RouteLLM)  
4. **Speculative** — draft/verify tokens (SLED, edge SD 2510.11331)  

MKM is **type 1 + structured handoff**, not layer split or token speculative.

### II.2 Scheduling & routing at the edge

| Work | Method | Result (paper) |
|------|--------|----------------|
| NSGA-II 2507.15553 | Pareto router table | 34.9% cost ↓ @ 95.2% quality |
| CE-CoLLM 2411.02829 | Early exit + async upload | 84.53% offload |
| HybridFlow 2512.22137 | DAG subtask utility routing | budget-aware |
| PerLLM 2405.14636 | UCB edge-cloud scheduling | 2.2× throughput |
| Dynamic Q-L 2508.11291 | BERT router + KV switch cost | 5–15% latency ↓ |

**MKM `[HYPO]` Privacy Shield:** edge emits `ollama_shallow_router_output_v1` only — **metadata handoff**. Literature supports direction; **MKM lacks formal privacy proof or enforced air-gap code audit.**

### II.3 Orchestration Gap (hybrid inference survey)

Academic term for MKM’s practical split:

- **System 1 (fast):** shallow route, pin inject, schema emit  
- **System 2 (slow):** RAG bridge, cloud reasoning, gold eval  

MKM implements **fixed contract** (schema + guards) vs learned orchestrator — valid solo-dev strategy per survey’s “static heuristics first” recommendation.

---

## Part III — Narrative: Routing economics & validation (Plane 3)

### III.1 Benchmark timeline

```
2023 FrugalGPT, LLMLingua → cost awareness
2024 RouterBench, RouteLLM → standardized eval
2025 RouterEval, RouterArena, IRT-Router → scale + commercial
2026 LLMRouterBench, R2-Bench, ORBIT, EquiRouter/RCI → Oracle gap + collapse
```

### III.2 LLMRouterBench key findings (2601.07206) — Tier 0 merge

- **400K+ instances**, 21 datasets, **33 models**, 10 baselines  
- Top routers: up to **~4% PerfGain**, **~31.7% CostSave** vs Best Single  
- **OpenRouter** can **underperform** Best Single (-24.7% in paper table footnote context)  
- **Model-recall failure** dominates Oracle gap — when only one small model is correct, routers miss it  
- **Embedding choice** barely matters — routing signal is in **query-model fit**, not embedder  

**MKM lesson:** Gold 12/12 proves **structural routing** on Logos queries; **does not** prove cost-optimal cloud routing — need `routing_oracle_gap`.

### III.3 Metrics MKM should adopt

| Metric | Source | MKM implementation |
|--------|--------|-------------------|
| routing_oracle_gap | RouterBench Oracle | `[Needs experiment]` pytest |
| QNC / rQNC | deferral curve | bench JSON column |
| RCI | EquiRouter 2602.03478 | monitor collapse to cloud-only |
| citation_pass_rate | internal | gold attribution |
| cloud_skip_ratio | CE-CoLLM analogy | % queries handled shallow-only |

**Do not use RET (2605.09294)** for routing — different paper (interpretability macrostates).

---

## Part IV — OSS, MCP, EU (merged operational)

### IV.1 Secret sprawl (GitGuardian 2026 + MCP)

- **~28.6M+** new secrets on public GitHub (2025 trajectory — verify in PDF)  
- **MCP configs: 24,008** unique secrets; **2,117** validated  
- **AI-assisted commits ~2×** leak rate  
- **Shai-Hulud 2:** 33k+ unique secrets on 6.9k machines  

**MKM P0 checklist:**

- [ ] gitleaks pre-commit  
- [ ] `SECURITY.md`  
- [ ] Audit `.cursor/mcp.json` + NotebookLM profile  
- [ ] Optional ggshield Cursor hooks  

### IV.2 EU CRA / PLD (merged, not legal advice)

**Safe OSS narrative for README:**

> Non-commercial research release under MIT. Not medical or investment advice. Software supplied outside commercial activity where applicable; see EU CRA OSS FAQ. Sponsors/paid SLA may change obligations.

**Unsafe:** “Disclaimer makes PLD/CRA immunity.”

### IV.3 SEND_GATE (unchanged)

```
OPEN   → oss_github_release
HOLD   → grants · B2B · ads
LOCKED → track_a_live_trading
```

---

## Part V — MKM measured vs Tier 0 external (master table)

| Topic | Tier 0 / literature | MKM measured | Public README |
|-------|----------------------|--------------|---------------|
| Token reduction | LLMLingua ~20× | shallow inject **99.6%** vs naive paste (orchestration bench, not cloud API $0) | **Yes** with scope |
| Cost routing | RouteLLM 2–3.6× | not measured | Related work only |
| Cloud offload | CE-CoLLM 84% | not measured | No |
| Memory accuracy | ByteRover LoCoMo SOTA | gold **12/12** CPU + shallow live **16/16** (domain-specific) | Yes with scope |
| JSON cap | — | ultra_min **56%** smaller | Yes + gold guard |
| Routing collapse | RCI metric | not measured | No |
| Reference federation | Mem0 / file-tree wikis | Vault2 **6 pointers** + catalog `research_ssot` | Yes — pointer-only |
| Deep lane | cloud LLM verify | `-IncludeDeepLive` reproduce bundle | Bench only · HOLD public |

---

## Part VI — Unified catalog (62 sources)

### VI.A Edge–cloud & inference (14)

| # | ID | Title |
|---|-----|-------|
| 1 | 2411.02829 | CE-CoLLM |
| 2 | 2507.15553 | NSGA-II edge LLM routing |
| 3 | 2512.23310 | Splitwise Lyapunov DRL |
| 4 | 2505.14085 | CE-LSLM |
| 5 | 2507.16731 | Edge SLM–cloud LLM survey |
| 6 | 2512.22137 | HybridFlow |
| 7 | 2508.11291 | Dynamic Q-L edge routing |
| 8 | 2502.04392 | Division-of-Thoughts |
| 9 | 2405.14636 | PerLLM |
| 10 | 2506.09397 | SLED speculative edge |
| 11 | 2510.11331 | Speculative decoding edge net |
| 12 | 2604.22906 | Network Edge LLM survey |
| 13 | OpenReview OIrJI53MvN | Hybrid inference systems survey |
| 14 | TST 9010166 | Edge LLM inference survey |

### VI.B Memory & context (22)

| # | ID | Title |
|---|-----|-------|
| 15 | 2310.08560 | MemGPT |
| 16 | 2604.01599 | ByteRover |
| 17 | 2410.14052 | MemTree SCHEMAS |
| 18 | 2507.22925 | H-MEM |
| 19 | ACL 2025-1575 | HiAgent |
| 20 | 2510.24699 | AgentFold |
| 21 | 2512.22087 | Context as a Tool |
| 22 | 2401.18059 | RAPTOR |
| 23 | 2405.14831 | HippoRAG |
| 24 | 2505.22006 | EHC |
| 25 | EMNLP 2025-1318 | MemoryOS |
| 26 | NeurIPS 2025 | G-Memory |
| 27 | 2603.07670 | Memory agents survey |
| 28 | 2602.05665 | Graph memory survey |
| 29 | 2602.19320 | Agentic memory anatomy |
| 30 | 2602.06052 | Memory second half survey |
| 31 | 2605.06716 | Storage→Experience survey |
| 32 | 2603.21564 | Hierarchical memory theory |
| 33 | 2604.01707 | Modular memory framework |
| 34 | 2511.02424 | ReAcTree |
| 35 | A-MEM 2025 | Agentic memory network |
| 36 | Mem0 2025 | Industrial MAG |

### VI.C Routing & cost (16)

| # | ID | Title |
|---|-----|-------|
| 37 | 2403.12031 | RouterBench |
| 38 | 2406.18665 | RouteLLM |
| 39 | 2601.07206 | LLMRouterBench |
| 40 | 2602.03478 | EquiRouter RCI |
| 41 | 2602.02823 | R2-Router R2-Bench |
| 42 | 2606.18774 | RouteJudge ORBIT |
| 43 | EMNLP 2025-208 | RouterEval |
| 44 | ACL 2025-761 | IRT-Router |
| 45 | 2510.00202 | RouterArena |
| 46 | 2305.05176 | FrugalGPT |
| 47 | HybridLLM ICLR 2024 | cascade |
| 48 | GraphRouter ICLR 2025 | GNN routing |
| 49 | RouterDC NeurIPS 2024 | contrastive |
| 50 | CARROT Router | cost-accuracy |
| 51 | vLLM Semantic Router | category route |
| 52 | Universal Router | K-means clusters |

### VI.D Compression & related (4)

| # | ID | Title |
|---|-----|-------|
| 53 | 2310.05736 | LLMLingua |
| 54 | 2310.06839 | LongLLMLingua |
| 55 | 2605.09294 | Representational ET (not routing) |
| 56 | Selective Context 2023 | baseline |

### VI.E OSS / industry (6)

| # | Source | Topic |
|---|--------|-------|
| 57 | GitGuardian SSS 2026 | Secret sprawl MCP |
| 58 | EU CRA 2024/2847 | OSS scope |
| 59 | EU PLD 2024/2853 | Product liability |
| 60 | OpenAI 2025 | ChatGPT memory product |
| 61 | LMSYS RouteLLM blog | commercial routing |
| 62 | MKM policy JSON | forbidden_public_claims |

### VI.F Gemini / delegation supplement (2026-06-20)

| # | ID | Title | MKM tag |
|---|-----|-------|---------|
| 63 | 2512.10398 | Confucius Code Agent | hierarchical scope / compress |
| 64 | 2508.00031 | GCC Git Context Controller | IDE file-backed memory |
| 65 | 2510.11967 | Context-Folding / FoldGRPO | fold cluster |
| 66 | OpenReview | ShallowKV | KV-layer — **≠** MKM text shallow inject |
| 67 | arXiv | HIPIF | subgoal information folding |
| 68 | arXiv | CoIn | opaque API reasoning token audit |
| 69 | arXiv | Token Inflation | provider overcharge / billing |
| 70 | delegation sweep | Monetization reality (GitGuardian·Continue·ByteRover) | B-track GTM `[HYPO]` |

---
## Part VI.G — Incremental raw drop (2026-06-22)

| # | ID | Title | Source raw | MKM tag |
|---|-----|-------|------------|---------|
| 71 | 2505.11764 | 2505.11764 | `docs/research/raw/universal_root_lexicon_matrix_cursor_sweep_2026-06-21.md` | raw_drop `[HYPO]` |
| 72 | 2304.12404 | 2304.12404 | `docs/research/raw/universal_root_lexicon_matrix_cursor_sweep_2026-06-21.md` | raw_drop `[HYPO]` |
| 73 | 2601.08881 | 2601.08881 | `docs/research/raw/universal_root_lexicon_matrix_cursor_sweep_2026-06-21.md` | raw_drop `[HYPO]` |
| 74 | 2404.16130 | 2404.16130 | `docs/research/raw/universal_root_lexicon_matrix_cursor_sweep_2026-06-21.md` | raw_drop `[HYPO]` |
| 75 | 2505.11764 | 2505.11764 | `docs/research/raw/universal_root_lexicon_matrix_gemini_prompt_v1.md` | raw_drop `[HYPO]` |

## Part VII — Implementation roadmap (merged priority)

### P0 — before public push

1. gitleaks + `SECURITY.md`  
2. MCP audit script  
3. README: link **this merged doc** as Related Work SSOT  

### P1 — narrative (**FACT 2026-06-20**)

4. README EN paragraph (from rev.2 §8c)  
5. Measured vs Research table (Part V) — **done in this merged doc**  
6. Vault2 reference pointer registry + federated catalog — **exit 0** (`check_mkm_reference_pointer_registry_v1.py` · `build_mkm_knowledge_catalog_v1.py`)  
7. MERGED doc linked as `ref:research:nextgen_hybrid_merged` — **no ops/LTM body merge**  

### P2 — science

6. Shadow eval `routing_oracle_gap`  
7. RCI monitoring if cost router added  
8. AKL labels on wiki nodes `[HYPO]`  

### P3 — Tier 0 refresh (**FACT 2026-06-20**)

9. Gemini supplement → `raw/gemini_hcm_4vault_monetization_2026-06-20.md` — **done**  
10. MERGED Part X conflict filter + VI.F delta — **done**  
11. Git track `docs/research/**` for GitHub Related Work link — **done** (see Part IX)

---

## Part VIII — Overclaim firewall (merged)

| # | Forbidden public claim |
|---|------------------------|
| 1 | 242× / DMF as MKM KPI |
| 2 | LLMLingua 20× as MKM product |
| 3 | NSGA-II implemented |
| 4 | ByteRover-equivalent without AKL code |
| 5 | HCM ISO standard |
| 6 | RET routing equivalence |
| 7 | OpenRouter-style savings guarantee |
| 8 | EU immunity from disclaimer |
| 9 | SEND OPEN = live trading |
| 10 | Ollama shallow = primary SSOT over ops memory |
| 11 | Cloud API cost **zero** / Cursor limits **mocked** |
| 12 | Hallucination **eliminated** (citation_lock = arXiv IDs in md only) |
| 13 | Bulk-merge external docs into `ops_memory_index` / LTM graph |
| 14 | Shallow router **replaces** deep RAG or Vault 4 wiki |
| 15 | LongMemEval / LoCoMo **95.6%** as MKM score (Gemini projection) |
| 16 | Routing **99.8%** / security **0.00%** / fraud **94.7%** as MKM KPI |
| 17 | Merkle + CoIn **shipped** — proves hallucination elimination |
| 18 | NSGA-II / Ω sleep engine **production** scheduler |
| 19 | **Patent moat** / **global standard** / **군림** / **완벽 정면 돌파** |
| 20 | Gemini competitor matrix scores as **MKM bench** without citation |

---

## Part X — Gemini Tier 0 conflict filter (2026-06-20)

| Gemini / whitepaper draft claim | Filter | Public wording |
|----------------------------------|--------|----------------|
| MKM LongMemEval 95.6% | **DROP** | Not measured — omit |
| Oracle gap 0.0 = routing solved | **NARROW** | 16 golden in-domain shallow bench |
| 99.6% = cloud cost zero | **NARROW** | Orchestration inject vs naive paste |
| Merkle + CoIn in MCP (deployed) | **HYPO** | Tier 2 provenance spike only |
| NSGA-II offload formalized | **HYPO** | Literature cite; no scheduler code |
| Desktop companion → server $0 | **DROP** | Local compute; Cursor/API fees remain |
| Open-core $10/seat + advisory | **OK** | `[HYPO]` GTM — align GitGuardian pattern |
| ByteRover = only rival | **NARROW** | Closest analog; MemGPT/Mem0/HybridLLM cluster |

**SSOT for unfiltered Gemini body:** `docs/research/raw/gemini_hcm_4vault_monetization_2026-06-20.md`

---

## Part IX — Reproducibility (merge manifest)

**Tier 0 files:**  
- `docs/research/raw/tier0_hybrid_ai_web_sweep_2026-06-20.md`  
- `docs/research/raw/delegation_hcm_4vault_moat_deep_sweep_2026-06-20.md`  
- `docs/research/raw/gemini_hcm_4vault_monetization_2026-06-20.md`  

**Tier 1 files:**  
- `docs/research/NEXT_GEN_HYBRID_AI_MKM_THEORY_IMPLEMENTATION_LIT_REVIEW_2026-06-20.md`  
- `docs/research/DELEGATION_HCM_4VAULT_MOAT_LIT_REVIEW_2026-06-20.md`  

**Merged SSOT (this file):** `docs/research/NEXT_GEN_HYBRID_AI_MKM_MERGED_LIT_REVIEW_2026-06-20.md`

**Search rounds total:** 8 Exa/Web + Tier 1 prior 6 + delegation 32 + Gemini supplement  
**Exa rate limit:** hit once; WebSearch fallback  
**Gemini Deep Research:** ingested 2026-06-20 → `raw/gemini_hcm_4vault_monetization_2026-06-20.md` (filtered by Part X)  

**MKM reproduce bench:**

```powershell
cd C:\workspace
py scripts/run_mkm_ltm_orchestration_bench_bundle_v1.py
py scripts/check_mkm_solo_oss_release_readiness_v1.py
py scripts/check_mkm_reference_pointer_registry_v1.py
py scripts/build_mkm_knowledge_catalog_v1.py
py -m pytest tests/test_mkm_reference_pointer_registry_v1.py -q
powershell -File scripts\Run-OllamaShallowHybridReproduceBundle_v1.ps1
powershell -File scripts\Run-OllamaShallowHybridReproduceBundle_v1.ps1 -IncludeDeepLive
py scripts/run_mkm_merged_lit_review_gate_chain_v1.py --input docs/research/NEXT_GEN_HYBRID_AI_MKM_MERGED_LIT_REVIEW_2026-06-20.md
```

**Next Tier 2:**

```text
딥리서치 Tier 2: routing_oracle_gap → tests/test_ollama_shallow_router_bench_v1.py exit 0
[HYPO] P2: allowlist ingest + Ω sleep consolidation — after P1 git push; single Ollama model · nightly window
```

---

*Classification: B-track · Not legal advice · Track A live LOCKED · `[HYPO]` where noted*

## Re-merge manifest (auto)

- last_remerge_utc: `2026-06-22T09:39:57Z`
- merge_mode: `incremental_patch_full_gate`
- raw_file_count: `8`
