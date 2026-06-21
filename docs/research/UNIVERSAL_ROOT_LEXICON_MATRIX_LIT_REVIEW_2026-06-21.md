# Universal Root Lexicon Matrix — Layer A/B/C Hierarchical Gating [HYPO]

> **Superseded for SSOT by:** `docs/research/UNIVERSAL_ROOT_LEXICON_MATRIX_MERGED_LIT_REVIEW_2026-06-21.md` (Tier 0→1 merge). Keep this file for expanded sections and BibTeX.

**Date:** 2026-06-21  
**Skill:** mkm-deep-research Tier 1 (Cursor direct sweep)  
**Track:** B-track · `research_only` · `send_gate: HOLD`  
**Tier-0 input:** `docs/research/raw/universal_root_lexicon_matrix_gemini_prompt_v1.md`  
**Related:** `ROOT_LEXICON_41K_4D_EVOLUTION_LIT_REVIEW_2026-06-21.md` · `LOGOS_GRAPHRAG_4D_OLLAMA_LIT_REVIEW_2026-06-21.md`  
**Raw sweep:** `docs/research/raw/universal_root_lexicon_matrix_cursor_sweep_2026-06-21.md`

---

## Executive synthesis

Constructing a **“Universal Minimal Core Lexicon” that replaces a 41k corpus anchor** is **not supported** by MKM disk evidence or mainstream NLP theory. What **is** feasible—and already partially built—is a **three-layer hierarchical gating matrix**:

| Layer | Role | Size order | MKM status |
|-------|------|------------|------------|
| **A — Universal Root Gate** | Cross-domain tags, shallow routing, NSM prime explications | ~65 primes (+ molecules) | **Partial** — NSM crosswalk audit exists; DeepNSM not wired |
| **B — Corpus Anchor Matrix** | Retrieval, compression lookup, lemma/entity sidecars | ~41k rows + graph edges | **Production rail** — Track A compress + Logos Phase 10 subgraph |
| **C — MDL Lexicon Pruner** | Surface redundancy removal without semantic replacement | Target: 10–30% row reduction | **Not run** — Morfessor-class PoC pending |

**Key empirical anchor:** NSM↔41k **500-pair** audit (Phase 11-A) → `prime_hit_rate=0.0701`, `english_only_distortion_rate=0.8061`, `gate_ok=false`. (100-pair baseline: 8.4% / 86.3%.) Therefore Layer A **gates and labels**; Layer B **retrieves and compresses**. English-only distortion is the metric Layer A↔B crosswalk must drive down—not Hit@k alone.

**Orthogonality:** Literature supports **soft routing alignment** (TAG-MoE, select-then-route), not perfect disjoint semantic matrices in natural language. Use MDL + conceptual labeling for **minimal covering sets**, not linear algebra “perfect orthogonality.”

---

## Section 1 — Information theory vs 41k anchors

### 1.1 What 41k actually is (Fact-Lock)

- **41,658 rows** = normalized surface types from Logos corpora + Strong/MorphHB stickers.
- **Not:** Strong inventory completeness, NSM prime set, or compute-optimal vocabulary (cf. scaling-law vocab work).
- **Track A contract:** lexicon lookup ON, `apply_gematria_4d_bridge_policy: false` on Golden-40 compress bench.

### 1.2 MDL and redundancy (Layer C)

**Morfessor EM+Prune** (Grönroos et al., LREC 2020; arXiv:2003.03131) iteratively prunes a seed lexicon until MDL cost rises—direct template for **surface deduplication** within 41k without deleting semantic anchors.

**Conceptual Labeling** (Sun et al., IJCAI 2015) selects a **minimum concept set** covering a bag-of-words under MDL—template for **Layer A prime selection** given a query/corpus slice.

**Semantic Tokenizer** (arXiv:2304.12404) explicitly splits vocabulary into semantic vs coverage segments—formal analog of **Layer A vs Layer B**.

### 1.3 Bottleneck diagnosis

| Bottleneck | Cause | Layer fix |
|------------|-------|-----------|
| English-only distortion 86%+ | NSM primes matched via English string lookup in 41k | A↔B crosswalk via explication + G/H alignment |
| prime_hit 8.4% | 41k is corpus-surface, not prime-indexed | DeepNSM explication → map to Strong's, not English token |
| Retrieval misses (pre-Phase 10) | Wrong bridge ranking, not missing 41k rows | B-side sidecars + path-first order (done v2.0) |
| Compress Jaccard drop when lexicon ON | Tradeoff: ~50%→~47% saving for +Jaccard | Layer C prune may recover bytes without new semantics |

---

## Section 2 — Layer A/B/C architecture blueprint

```
[Query / corpus slice]
        │
        ▼
┌───────────────────────────────────────┐
│ Layer A — NSM Root Gate [HYPO]        │
│ · DeepNSM 1B/8B explication (shadow)  │
│ · Ollama shallow: domain_tag + primes │
│ · Select-then-route taxonomy prune    │
└───────────────┬───────────────────────┘
                │ sidecar selector
                ▼
┌───────────────────────────────────────┐
│ Layer B — Corpus Anchor Matrix        │
│ · 41k master codebook lookup          │
│ · Logos lemma / OSI / theographic     │
│ · concept_bridge paths                │
└───────────────┬───────────────────────┘
                │ optional offline batch
                ▼
┌───────────────────────────────────────┐
│ Layer C — MDL Pruner                  │
│ · Morfessor EM+Prune on surface forms │
│ · Jaccard stability gate on Golden-40 │
└───────────────────────────────────────┘
```

### 2.1 Layer A — DeepNSM integration path

- **Paper:** Baartmans et al., *Towards Universal Semantics with LLMs* (arXiv:2505.11764, 2025).
- **Repo:** [OSU-STARLAB/DeepNSM](https://github.com/OSU-STARLAB/DeepNSM) — 1B/8B HuggingFace models, `baartmar/nsm_dataset`.
- **MKM use:** Offline shadow explication for crosswalk pairs—not online cloud dependency.
- **Collision:** Ignore 2020 CV “DeepNSM” (scene memorability)—different paper.

### 2.2 Layer B — Sidecar pattern (proven)

Logos Phase 10: **Hit@1/3/8 = 100%** on 12 gold queries with lemma + xref + theographic + gematria sidecars. This validates **anchor + sidecar** over flat universal matrix.

### 2.3 Layer C — MDL prune acceptance criteria

| Metric | Gate (proposed `[HYPO]`) |
|--------|--------------------------|
| Golden-40 Jaccard | ≥ 0.885 (no collapse) |
| Golden-40 saving | ≥ 46.5% (max −0.5pp vs 47.12% baseline) |
| Row count reduction | 5–15% first pass |
| NSM distortion | english_only_distortion ≤ 0.60 on 500-pair audit |

---

## Section 3 — Cross-domain mapping (TCM · IT · Legal)

**Literature:** Interlingual lexical DB surveys (Bond & Vossen 2023) — **no unbiased single hub**. **Select-Then-Route** (EMNLP 2025 Industry) — taxonomy narrows candidate space before expensive routing.

**MKM mapping:**

| Domain | Layer A (gate tag) | Layer B (anchor) | Sidecar |
|--------|-------------------|------------------|---------|
| Logos / scripture | `logos`, NSM primes: KNOW, GOOD, BAD | 41k G/H + lemma graph | Gnosis, OSI, theographic |
| TCM / 한의 | `clinical`, primes: BODY, FEEL | hangul overlay 41676 `[HYPO]` | patient_track_b memory |
| IT / infra | `infra`, primes: DO, HAPPEN | ops pins + log token aliases | shallow router fixtures |
| Legal | `legal`, primes: SAY, WANT, NOT | extension overlay (future) | `[Needs experiment]` |

**English-only distortion mitigation:** For each NSM prime, store **(en_probe, greek_probe, hebrew_probe)** in crosswalk fixture; accept hit only if **original-language probe** matches or DeepNSM explication links to Strong's.

---

## Section 4 — Empirical validation framework

### 4.1 Split metrics (never collapse)

| Plane | Metric | Scope | MKM script |
|-------|--------|-------|------------|
| Compress | saving %, Jaccard | Golden-40 offline | comp atom / track_a chain |
| Retrieve | Hit@1/@3/@8 | Logos gold fixture | `run_logos_subgraph_gold_eval_v1.py` |
| Route | routing_oracle_gap | Shallow domain fixtures | `build_ollama_shallow_routing_oracle_gap_v1.py` |
| Distortion | prime_hit, english_only_distortion | NSM crosswalk | `run_nsm_41k_lexicon_crosswalk_audit_v1.py` |
| Cost | cloud_skip_ratio | Shallow preprocess only | shallow bench report |

### 4.2 RouterBench / RouteLLM analogy

- **RouterBench Oracle** = always pick best model—upper bound.
- **MKM routing_oracle_gap** = expected_domain_tag vs parsed_domain_tag on golden fixtures—**same formalism, different label space**.
- RouteLLM shows **2×+ cost reduction** with learned routers—validates local-first gate economics **at LLM-pair level**; MKM extends to **lexicon/sidecar selection**.

---

## Literature table (Tier 1)

| # | Source | Year | Method | MKM Layer | Tag |
|---|--------|------|--------|-----------|-----|
| 1 | Baartmans et al., DeepNSM | 2025 | NSM explication LLM | A | [Adoptable now] shadow |
| 2 | Wierzbicka/Goddard NSM | 1970s+ | Semantic primes | A | [Adoptable now] theory |
| 3 | Grönroos, Morfessor EM+Prune | 2020 | MDL lexicon prune | C | [Adoptable now] |
| 4 | Sun et al., Conceptual Labeling | 2015 | MDL + semantic network | A↔B | [Adoptable now] |
| 5 | Tao et al., Scaling Laws w/ Vocab | 2024 | Compute-optimal vocab | B sizing | [Adoptable now] |
| 6 | Semantic Tokenizer | 2023 | Dual semantic/coverage vocab | A/B split | [Needs experiment] |
| 7 | Select-Then-Route | 2025 | Taxonomy + cascade | A gate | [Adoptable now] |
| 8 | RouteLLM | 2024 | Preference router | cost gate | [Adoptable now] |
| 9 | RouterBench | 2024 | Multi-LLM routing bench | oracle gap | [Adoptable now] |
| 10 | TAG-MoE | 2026 | Task-aware gating | soft orthogonality | [Needs experiment] |
| 11 | Microsoft GraphRAG | 2024 | Graph community RAG | B retrieve | [Adoptable now] |
| 12 | Bond & Vossen, interlingual MLDB | 2023 | Hub comparison | overclaim guard | [Adoptable now] |
| 13 | Navigli, BabelNet | — | Supra-lingual synsets | B extension | [Needs experiment] |
| 14 | ConceptNet | 2017+ | Commonsense graph | B assist | B-track only |
| 15 | MemTree / hierarchical memory surveys | 2025–26 | Context folding | Plane 2 | ≠ lexicon |

---

## Proposed MKM deltas (Phase 11)

| ID | Delta | Priority | Tag |
|----|-------|----------|-----|
| **D11-1** | `UNIVERSAL_ROOT_GATE_SPEC_V1.json` — Layer A/B/C schema + metric gates | P0 | **done** — `check_universal_root_gate_spec_v1.py` |
| **D11-2** | NSM crosswalk **100→500** pairs + distortion gate trend | P0 | `run_logos_graphrag_phase11a_chain_v1.py` |
| **D11-3** | DeepNSM **shadow chain** (1B, offline) → explication JSONL for crosswalk | P1 | GPU-adjacent |
| **D11-4** | Morfessor-style MDL prune PoC on 41k export → Jaccard report | P1 | Layer C |
| **D11-5** | Shallow router output: optional `nsm_prime_tags[]` (≤3) | P1 | **done** — `run_p3_root_nsm_wire_chain_v1.py` |
| **D11-6** | Gold fixture **12→48** (extension merge) + Hit@k re-eval | P0 | done — `logos_gold_query_eval_v1.json` v1.2.0 |
| **D11-7** | `themed_dan_aramaic` human signoff (registry 89.5%) | P2 | governance |

---

## Overclaim firewall

| Claim | Verdict |
|-------|---------|
| “41k replaced by 65 primes” | **Forbidden** — audit FAIL |
| “Perfect orthogonality achieved” | **Forbidden** — use soft gating |
| “Hit@8 100% = universal lexicon” | **Forbidden** — 12-query Logos only |
| “cloud_skip 1.0 = zero API cost OS-wide” | **Forbidden** — shallow scope |
| “DeepNSM proves theology routing” | **Forbidden** — explication quality only |
| “Layer A/B/C spec = Track A promotion” | **Forbidden** — `[HYPO]` until gates pass |

---

## Gemini Tier-0 adversarial filter (2026-06-21)

**Raw ingest:** `docs/research/raw/universal_root_lexicon_matrix_gemini_report_2026-06-21.md`

Gemini Deep Research returned a persuasive synthesis aligned with Layer A/B/C **structure** but with several **Fact-Lock violations**. Staff ruling:

| Gemini claim | MKM disposition |
|--------------|-----------------|
| 96.8% LongMemEval vs Mem0/Letta/OMEGA table | **Unverified** — no `run_*` artifact; do not cite |
| CSR 0.98 · 94.2% token savings (OS-wide) | **Scope error** — MKM `cloud_skip_ratio` = shallow router fixtures only |
| Perfect NSM orthogonality · column-disjoint matrix | **Reject** — natural language ≠ orthogonal basis |
| “MKM Technical Specification v4” on disk | **False at ingest** — spec not committed |
| Wanda/SparseGPT prunes lexicon tokens | **Misapplied** — weight pruning tools |
| Merkle + on-chain hybrid blockchain | **`[HYPO]`** — tenant diff Merkle in Python first |
| English-only distortion root cause | **Accept** — consistent with 100-pair audit 86.32% |
| MDL + 4D compound gating + local router | **Salvage `[HYPO]`** — Phase 11 gate spec |

**Operational rule:** Gemini raw = brainstorming input only. Promotion path remains **NSM 500-pair audit trend + gold Hit@k + GATE_SPEC JSON**, not external benchmark tables.

---

## Open questions

1. **Primary KPI for “better than 41k”:** compress Jaccard vs crosswalk distortion vs Hit@k—which gate blocks promotion?
2. **DeepNSM 8B on Windows:** GPU requirement vs 1B shadow-only default for solo ops?
3. **MDL prune + must_keep:** `master_codebook_lexicon_v1_bridge` must_keep rows—exempt G/H linked rows from prune?
4. **Minimal English vs NSM primes:** Layer A uses 65 primes or expanded Minimal English (~200)—cross-lingual tradeoff?

---

## Reproducibility

```powershell
# Gate spec validate + eval
py scripts/run_logos_graphrag_phase11b_chain_v1.py

# NSM distortion baseline (500-pair default)
py scripts/run_logos_graphrag_phase11a_chain_v1.py

# Legacy 100-pair
py scripts/run_nsm_41k_lexicon_crosswalk_audit_v1.py --fixture-100 --expected-pairs 100

# Shallow oracle gap
py scripts/run_ollama_shallow_router_bench_v1.py
py scripts/build_ollama_shallow_routing_oracle_gap_v1.py

# Compress rail
py scripts/comp_atom02_lexicon_must_keep_analysis_v1.py

# Phase 10 chain
py scripts/run_logos_graphrag_phase10_miss_tune_chain_v1.py
```

**External:** arXiv:2505.11764 · arXiv:2003.03131 · IJCAI 2015/191 · arXiv:2406.18665 · arXiv:2403.12031 · EMNLP 2025 StR paper.

---

## BibTeX (selected)

```bibtex
@misc{baartmans2025deepnsm,
  title={Towards Universal Semantics with Large Language Models},
  author={Baartmans, Raymond and Raffel, Matthew and Vikram, Rahul and Deringer, Aiden and Chen, Lizhong},
  year={2025},
  eprint={2505.11764},
  archivePrefix={arXiv}
}
@inproceedings{gronroos2020morfessor,
  title={Morfessor {EM+Prune}: Improved Subword Segmentation with Expectation Maximization and Pruning},
  author={Gr{\"o}nroos, Stig-Arne and Virpioja, Sami and Kurimo, Mikko},
  booktitle={LREC 2020},
  year={2020}
}
@inproceedings{sun2015conceptual,
  title={On Conceptual Labeling of a Bag of Words},
  author={Sun, Xiangyan and Xiao, Yanghua and Wang, Haixun and Wang, Wei},
  booktitle={IJCAI 2015},
  year={2015}
}
@article{ong2024routellm,
  title={RouteLLM: Learning to Route LLMs with Preference Data},
  year={2024},
  eprint={2406.18665},
  archivePrefix={arXiv}
}
```
