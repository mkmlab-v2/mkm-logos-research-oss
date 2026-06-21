# Universal Root Lexicon Matrix — MKM 병합 리뷰 (Tier 0→1) [HYPO]

**Merged:** 2026-06-21 · **Skill:** mkm-deep-research v1.2 Tier 0→1  
**Track:** B-track · `research_only` · `send_gate: HOLD`

> **Supersedes for SSOT:** This file is the canonical merge. Tier-1-only draft: `docs/research/UNIVERSAL_ROOT_LEXICON_MATRIX_LIT_REVIEW_2026-06-21.md` (keep for detail; cite MERGED for promotion decisions).

---

## Merge manifest

| Tier | File | Role |
|------|------|------|
| **0** | `docs/research/raw/universal_root_lexicon_matrix_gemini_prompt_v1.md` | Tier0 DR prompt SSOT |
| **0b** | `docs/research/raw/universal_root_lexicon_matrix_gemini_report_2026-06-21.md` | Gemini raw ingest + adversarial index |
| **0c** | `docs/research/raw/universal_root_lexicon_matrix_cursor_sweep_2026-06-21.md` | Cursor Exa/web sweep (Tier 1 raw) |
| **1** | `docs/research/UNIVERSAL_ROOT_LEXICON_MATRIX_LIT_REVIEW_2026-06-21.md` | MKM Fact-Lock synthesis + paper table |
| **Spec** | `docs/final/artifacts/UNIVERSAL_ROOT_GATE_SPEC_V1.json` | Layer A/B/C metric planes (D11-1) |
| **NL** | Notebook `14-universal-lexicon-dr` · uuid `47ffa7da-…` | Research sandbox only — not lens-pack refresh |

**Search rounds:** Tier 1 Cursor sweep (4+ rounds) · Gemini Tier0 external (commander paste, filtered)  
**Citation lock:** `docs/final/artifacts/UNIVERSAL_ROOT_LEXICON_MATRIX_LIT_REVIEW_2026-06-21_citation_lock_latest.json` · pass rate 1.0 (5 arXiv IDs)

---

## Key papers (fact_support catalog)

| arxiv_id | title |
|----------|-------|
| 2003.03131 | Morfessor EM+Prune: Improved Subword Segmentation with Expectation Maximization and Pruning |
| 2304.12404 | Semantic Tokenizer for Enhanced Natural Language Processing |
| 2505.11764 | Towards Universal Semantics With Large Language Models |
| 2406.18665 | RouteLLM: Learning to Route LLMs with Preference Data |
| 2403.12031 | RouterBench: A Benchmark for Multi-LLM Routing System |

---

## Executive synthesis (field vs MKM)

**Field consensus (salvageable):**

1. **No single universal lexicon replaces domain corpus anchors** — interlingual hubs (BabelNet, ConceptNet) are assistive, not compression SSOT.
2. **MDL / Morfessor-class pruning** removes surface redundancy without semantic replacement (Layer C template).
3. **NSM ~65 primes** are theory for cross-lingual gating — DeepNSM (arXiv:2505.11764) automates explication, not retrieval.
4. **Select-then-route** (taxonomy before expensive routing) matches Layer A shallow gate + Layer B sidecar pattern.
5. **RouterBench / RouteLLM** formalize oracle gap — MKM `routing_oracle_gap` on shallow fixtures is the analog.

**MKM Fact-Lock (must hold):**

| Fact | Value | Lane |
|------|-------|------|
| Corpus surface anchor | **41,658** rows | Track A compress fuel |
| Logos verse corpus | **31,102** `verse_id` | B-track RAG `[NON_GATING]` |
| NSM↔41k distortion (500-pair) | prime_hit ~7%, english_only ~80%, `gate_ok=false` | Layer A audit |
| Logos gold Hit@1/3/8 | 100% (48-query extension) | Layer B retrieve |
| Track A compress KPI | ~47.5% saving (raw), 4D bridge OFF | **not** NSM gate proof |

**Gemini Tier0 filtered out:** Mem0/Letta benchmark tables, CSR 0.98, 94.2% OS token savings, perfect NSM orthogonality, Wanda-on-lexicon, on-chain Merkle hero, fictitious “MKM Technical Specification v4”.

---

## Layer A/B/C unified blueprint

```
Query → Layer A (NSM gate / domain_tag / primes≤3) [HYPO]
      → Layer B (41k lookup + lemma/OSI/theographic sidecars) [production rail]
      → Layer C (MDL surface prune + Jaccard floor) [not_run → PoC]
```

**Promotion rule:** NL or Gemini prose **never** promotes Track A. Only `run_*` exit 0 + `UNIVERSAL_ROOT_GATE_SPEC` planes + raw KPI gates.

---

## Phase 11-E — NSM crosswalk repair (2026-06-21)

**Command:** `py scripts/run_logos_graphrag_phase11e_nsm_crosswalk_repair_chain_v1.py` · exit **0**

| Metric | raw (latin baseline) | shadow (DeepNSM explication sidecar) | Δ shadow−raw |
|--------|---------------------|--------------------------------------|--------------|
| `prime_hit_rate` | 0.0701 | 0.979 | +0.9089 |
| `english_only_distortion_rate` | 0.8061 | 0.014 | −0.7921 |
| `gate_ok` | **false** | **true** | — |
| `aligned_original_language_count` | 30 | 419 | — |

**GATE_SPEC:** `research_ready_decision=B_TRACK_RESEARCH_READY` · enabled planes all OK · **`send_gate: HOLD`** · **`track_a_promotion_forbidden: true`**

**Interpretation:** Shadow metrics are **operational (post-explication sidecar included)** — not raw NSM string lookup quality. Track A promotion still requires **raw** distortion trend, not repair-only uplift alone.

---

## Raw distortion experiments (2026-06-21)

**Flag:** `--orig-probes-only` on `run_nsm_41k_lexicon_crosswalk_audit_v1.py` — ignore English probe when greek/hebrew exist.

| Mode | prime_hit | distortion | gaps | gate_ok |
|------|-----------|------------|------|---------|
| raw_latin (baseline) | 7.01% | **80.61%** | 53 | false |
| orig_probes_only (no EN) | 7.01% | **0%** | 398 | false |
| orig_probes_only + shadow sidecar | **97.9%** | **0%** | 9 | true |

**Takeaway:** English probe was the distortion *signal* (80.6%); without EN, raw latin greek/hebrew rarely hit 41k (398 gaps). **Original-language alignment** (gematria sidecar) is the repair path — not deleting EN alone.

Reproduce:
```powershell
py scripts/run_nsm_41k_lexicon_crosswalk_audit_v1.py --orig-probes-only --expected-pairs 500 --out reports/nsm_41k_lexicon_crosswalk_audit_orig_only_v1_latest.json
py scripts/run_nsm_41k_lexicon_crosswalk_audit_v1.py --orig-probes-only --explication-sidecar docs/final/artifacts/deepnsm_shadow_explication_v1.jsonl --expected-pairs 500 --out reports/nsm_41k_lexicon_crosswalk_audit_orig_only_shadow_v1_latest.json
```

---

## Conflict table (Tier 0 vs Tier 1)

| Claim | Tier 0 (Gemini) | MKM ruling |
|-------|-----------------|------------|
| Replace 41k with 65 primes | Implied in hero copy | **Reject** — coexistence only |
| Perfect orthogonality | Yes | **Reject** — soft gating |
| LongMemEval 96.8% | Table | **Unverified** — no artifact |
| English distortion ~86% | Yes | **Accept direction** — audit confirms |
| MDL + local shallow router | Yes | **Salvage [HYPO]** — Phase 11 spec |
| cloud_skip ≈ 1.0 OS-wide | Yes | **Scope error** — fixture only |

---

## P0 / P1 roadmap (Phase 11)

| ID | Action | Status |
|----|--------|--------|
| D11-1 | `UNIVERSAL_ROOT_GATE_SPEC_V1.json` + `check_universal_root_gate_spec_v1.py` | **done** |
| D11-2 | NSM 500-pair audit + gold re-eval | **done** — raw `gate_ok=false`; shadow repair **done** (11-E) |
| D11-3 | DeepNSM 1B shadow explication JSONL | **done** — `run_logos_graphrag_phase11e_nsm_crosswalk_repair_chain_v1.py` |
| D11-4 | MDL prune PoC + Jaccard gate | **done** — Phase 11-D |
| D11-5 | Shallow `nsm_prime_tags[]` wire | **done** |
| D11-6 | Gold 12→48 fixture | **done** |

---

## Overclaim firewall (merged)

- Forbidden: “41k replaced by NSM”, “Hit@8 = universal lexicon”, “cloud_skip 1.0 = zero API OS”, “Layer spec = Track A GO”.
- Allowed: “Layer A/B/C [HYPO] research stack”, “distortion trend on 500-pair audit”, “Logos retrieve separate from NSM gate”.

---

## Reproducibility

```powershell
# Merge validation path
py scripts/run_logos_graphrag_phase11b_chain_v1.py
py scripts/run_logos_graphrag_phase11a_chain_v1.py

# Citation lock
py scripts/check_research_lit_review_citation_lock_v1.py --input docs/research/UNIVERSAL_ROOT_LEXICON_MATRIX_LIT_REVIEW_2026-06-21.md

# NL sandbox register (on-demand)
py scripts/register_notebooklm_research_sandbox_mcp_v1.py --no-select
```

**Related SSOT:** `ROOT_LEXICON_41K_4D_EVOLUTION_LIT_REVIEW_2026-06-21.md` · `LOGOS_GRAPHRAG_4D_OLLAMA_LIT_REVIEW_2026-06-21.md`
