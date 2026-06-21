# Cursor Tier 1 sweep — Hierarchical Universal Knowledge Gating Matrix

- generated_at_utc: 2026-06-21
- agent: Cursor (mkm-deep-research Tier 1)
- tier0_input: `docs/research/raw/universal_root_lexicon_matrix_gemini_prompt_v1.md`
- track: B `[HYPO]` · send_gate: HOLD
- search_rounds: R0 repo · R1 NSM/MDL · R2 routing · R3 bench · R4 MKM gap

---

## R0 — MKM disk facts (do not contradict)

| Fact | Source |
|------|--------|
| 41k = ~41,658 corpus surface types (Logos export), not NSM universal root | CENTRAL §41k · `export_master_codebook_v1.py` |
| NSM↔41k crosswalk 100-pair: prime_hit **8.42%**, english_only_distortion **86.32%**, gate **FAIL** | `reports/nsm_41k_lexicon_crosswalk_audit_v1_latest.json` |
| Logos subgraph gold (12q, router v2.0): Hit@1/3/8 **100%** with lemma sidecars | `reports/logos_subgraph_gold_eval_v1_latest.json` |
| Shallow router oracle_gap **0.0** on 16 fixtures (domain tag) | `reports/ollama_shallow_routing_oracle_gap_v1_latest.json` |
| Golden-40 compress: **47.12%** saving, Jaccard **0.889** (lexicon rail) | HN paste / comp atom reports |
| Phase 10-A: router v2.0 path-first ordering + concept affinity | `run_logos_subgraph_graphrag_router_v1.py` v2.0.0 |

---

## R1 — NSM + MDL + lexicon optimization

1. **Baartmans et al. 2025** — DeepNSM (arXiv:2505.11764): LLM-generated NSM explications; 1B/8B beat GPT-4o on prime usage metrics. **Layer A automation path**, not retrieval matrix.
2. **Wierzbicka/Goddard NSM** — ~65 semantic primes, Minimal English molecules. Linguistic universals claim; **computational routing unproven at scale**.
3. **Grönroos et al. 2020** — Morfessor EM+Prune (LREC): MDL lexicon pruning with autotune target size. **Layer C direct analog**.
4. **Sun et al. 2015** — Conceptual Labeling + MDL (IJCAI): minimal concept set covering bag-of-words via Probase. **Layer A→B crosswalk pattern**.
5. **Tao et al. 2024** — Scaling Laws with Vocabulary (NeurIPS): optimal vocab size scales with compute. **41k not globally optimal** — corpus/budget dependent.
6. **Semantic Tokenizer** (arXiv:2304.12404): dual V1/V2 split — semantic roots vs coverage segment. **Parallel to Layer A/B split**.

---

## R2 — Hierarchical routing (select-then-route)

7. **Select-Then-Route** (EMNLP 2025 Industry): taxonomy-guided decision-space reduction + cascade. **Layer A = taxonomy/prime tag; Layer B = expert/corpus route**.
8. **RouteLLM** (arXiv:2406.18665): preference-trained routers, cost-quality tradeoff. **cloud_skip analog at LLM-pair level**.
9. **RouterBench** (arXiv:2403.12031): Oracle router upper bound; learned routers lag oracle. **routing_oracle_gap formalism**.
10. **TAG-MoE 2026** (arXiv:2601.08881): task-aware gating aligns routing signature to semantic embedding. **Soft orthogonality via alignment loss**, not hard disjoint matrix.

---

## R3 — Graph / domain sidecars (MKM already doing Layer B)

11. Microsoft GraphRAG (arXiv:2404.16130)
12. Gnosis KG / Sinew / OSI / Theographic / scriptures-js — MKM external KG stack (Phase 1–9)
13. Bond & Vossen 2023 — interlingual lexical DBs: no unbiased single hub

---

## R4 — Adversarial / overclaim filter

| Overclaim | Verdict |
|-----------|---------|
| Replace 41k with 65 NSM primes | **REJECT** — audit prime_hit 8.4% |
| Perfect orthogonality in natural language | **REJECT** — use soft gating / MDL redundancy reduction |
| cloud_skip_ratio=1.0 for entire OS | **REJECT** — shallow preprocess scope only |
| Hit@8 91.7% → universal lexicon solved | **REJECT** — 12-query gold, Logos domain only |
| DeepNSM name collision | **WARN** — 2020 CV "DeepNSM" ≠ 2025 NSM LLM (OSU-STARLAB) |

---

## Executive conclusion (sweep)

**Feasible:** Hierarchical Layer A (NSM gate) + Layer B (corpus anchors + sidecars) + Layer C (MDL surface prune) as **coexisting rails**, not replacement.

**Not feasible without experiment:** Single minimal matrix outperforming 41k on **compression Jaccard + cross-domain routing + ancient-language alignment** simultaneously.

**Recommended Phase 11 pipeline (4 steps):**

1. **Extract** — multi-domain bag-of-words → DeepNSM explication candidates (shadow, local 1B)
2. **Align** — MDL conceptual labeling: map explications to 41k rows + Strong/G/H (expand crosswalk 100→500)
3. **Gate** — Ollama shallow router emits `domain_tag` + `nsm_prime_tags[]` (≤3) → sidecar selection
4. **Verify** — split metrics: compress (Jaccard), retrieve (Hit@k), route (oracle_gap), distortion (crosswalk audit)
