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
| D11-7 | Phase 11-F→O chains (wire/stress/ablation/closure/bridge/fact/NL) | **done** |
| D11-8 | Phase 11-P compress observe + Layer C MDL plane enable | **done** — compress plane **still disabled** (saving 46.0% < 46.5%) |

---

## Phase 11-F→O summary (2026-06-21)

| Chain | Result |
|-------|--------|
| **11-F** | NSM wire oracle_gap 0.0; sidecar ablation v2 — 17 configs, no regression |
| **11-G** | Live Ollama stress 32: hit **100%**, oracle_gap **0.0** |
| **11-H** | Evidence pack pytest (gate phase `11-*` prefix) |
| **11-I** | Shallow modelfile v1.3; target fixtures all hit |
| **11-J** | Themed DAN signoff q23/q47 pass |
| **11-K** | Sidecar ablation v3; deploy skipped when requested |
| **11-L** | `closure_ok=true` |
| **11-M** | Research↔impl bridge `bridge_ok=true` |
| **11-N** | Fact support pass_rate **1.0** |
| **11-O** | NL sandbox pack 7 files; register ok |

**GATE_SPEC (post 11-L refresh):** `research_ready_decision=B_TRACK_RESEARCH_READY` · distortion/retrieve/route OK · **`send_gate: HOLD`**

---

## Phase 11-P — compress observe + Layer C enable (2026-06-21)

**Command:** `py scripts/run_logos_graphrag_phase11p_compress_layerc_gate_chain_v1.py` · exit **0** expected when MDL gate + layer_c plane enabled

| Metric | raw (lexicon ON) | lexicon OFF (ablation) | GATE threshold |
|--------|------------------|------------------------|----------------|
| `global_token_saving_rate` | **45.99%** | 49.79% | min **46.5%** |
| `avg_reconstruction_fidelity_jaccard` | **0.902** | 0.867 | min **0.885** |

**Dual reporting:** lexicon ON is the Track A-aligned profile (bridge OFF). OFF is higher saving but drops lexicon fuel — not promotion path.

| Plane | Status (11-P) | Notes |
|-------|---------------|-------|
| `layer_c_mdl` | **enabled** | MDL PoC 15% row reduction, jaccard delta 0.0 pp |
| `compress` | strict fail | strict lexicon_on 45.99% — missing `domain_relaxed` overrides |

---

## Phase 11-Q — compress parity + plane enable (2026-06-21)

**Command:** `py scripts/run_logos_graphrag_phase11q_compress_parity_chain_v1.py` · exit **0**

**Root cause:** strict `comp_atom02` omitted `domain_relaxed_max_saving_*` from frozen active report run_config.

| Profile | saving | jaccard | GATE |
|---------|--------|---------|------|
| strict `lexicon_on` | **45.99%** | 0.902 | fail |
| **active_report_parity** | **47.12%** | 0.889 | **pass** |

**Planes after 11-Q:** `compress` **enabled** · `layer_c_mdl` **enabled** · `B_TRACK_RESEARCH_READY` · **`send_gate: HOLD`**

**NL push:** `push_notebooklm_universal_root_research_pack_nlm_v1.py` · **7/7 ok**

**DeepNSM HF 1B:** gematria translit sidecar only — HF A/B stub added in 11-R.

---

## Phase 11-R — cost plane + DeepNSM HF stub (2026-06-21)

**Command:** `py scripts/run_logos_graphrag_phase11r_cost_deepnsm_stub_chain_v1.py` · exit **0**

| Item | Result |
|------|--------|
| **cost plane** | **enabled** — `cloud_skip_ratio=1.0` (live-32 stress, fixture scope) |
| **all enabled planes** | distortion · retrieve · route · **cost** · compress · layer_c_mdl — **all OK** |
| **DeepNSM HF A/B** | stub manifest — gematria arm implemented; HF 1B `not_implemented` |
| **decision** | `B_TRACK_RESEARCH_READY` · **`send_gate: HOLD`** |

**Scope guard:** `cloud_skip_ratio=1.0` = shallow preprocess fixture only — **not** OS-wide zero API cost.

**HF next work:** `run_deepnsm_hf_explication_chain_v1.py` (GPU-adjacent) · paired 500-pair audit · raw/shadow dual report.

---

## Phase 11-S — HF gloss-stub A/B + evidence + NL sync (2026-06-21)

**Command:** `py scripts/run_logos_graphrag_phase11s_evidence_nl_sync_chain_v1.py` · exit **0**

| Arm | prime_hit | distortion | gate_ok | Notes |
|-----|-----------|------------|---------|-------|
| gematria shadow | **97.9%** | **1.4%** | true | translit index |
| **HF gloss-stub** | **98.13%** | **1.64%** | true | offline gloss-only — **not HF 1B weights** |
| Δ stub−gematria | +0.23pp | +0.24pp | — | operational sidecar compare only |

**Deliverables:** evidence pack refresh · GATE_SPEC phase **11-S** · NL push **11/11 ok**

**Caution:** HF stub uses gloss overlap heuristic — do **not** claim DeepNSM 1B model validated.

---

## Phase 11-T — layer stack closure signoff (2026-06-21)

**Command:** `py scripts/run_logos_graphrag_phase11t_layer_stack_closure_chain_v1.py` · exit **0**

| Check | Result |
|-------|--------|
| 6 planes enabled + OK | **true** |
| Layer A/B/C status | partial / production_rail / poc |
| `closure_ok` | **true** |
| pytest bundle | gate spec · MDL · bridge · evidence · deepnsm unit |
| GATE_SPEC phase | **11-T** |

**Artifact:** `docs/final/artifacts/universal_root_layer_stack_closure_v1_latest.json`

**Still HOLD:** `send_gate: HOLD` · `track_a_promotion_forbidden: true` — closure = B-track research stack only.

---

## Phase 12 — live bundle + public smoke (2026-06-21)

**Command:** `py scripts/run_logos_graphrag_phase12_live_public_chain_v1.py` · exit **0**

| Check | Result |
|-------|--------|
| Live bundle (`jemaai_core_ok`) | **true** |
| Showroom trust/viz public smoke | **true** |
| Layer stack closure (11-T carry) | **true** |
| Commercial readiness stack | **true** |
| OP30 tier-matrix + oracle preview smoke | **true** |
| All enabled planes OK | **true** |
| GATE_SPEC phase | **12** |

**Artifacts:** `reports/logos_graphrag_phase12_live_public_chain_v1_latest.json` · `reports/logos_phase12_live_bundle_v1_latest.json`

**Scope:** jemaai.cloud showroom HEAD probes (oracle v6, meaning topology, chronology overlay, logos health) + local mkmlife public schema — **public smoke only**, not Track A promotion.

**Still HOLD:** `send_gate: HOLD` · `track_a_promotion_forbidden: true`.

---

## Phase 13 — DeepNSM HF Ollama local-weights pilot (2026-06-21)

**Command:** `py scripts/run_logos_graphrag_phase13_deepnsm_hf_ollama_chain_v1.py` · exit **0**

| Check | Result |
|-------|--------|
| Backend | **ollama_local_weights_v1** (`gemma4:e2b`) |
| Pilot fixture | 100-pair crosswalk |
| Ollama calls / failures | **100 / 0** |
| avg latency | **1.62s** |
| prime_hit (pilot) | **100%** |
| distortion (pilot) | **0%** |
| vs gematria (500 ref) | Δ prime **+2.1pp** · Δ distortion **−1.4pp** |
| Phase 12 carry | **true** |
| All enabled planes OK | **true** |
| GATE_SPEC phase | **13** |

**Artifacts:** `reports/logos_graphrag_phase13_deepnsm_hf_ollama_chain_v1_latest.json` · `reports/deepnsm_hf_explication_ollama_chain_v1_latest.json` · `docs/final/artifacts/deepnsm_hf_explication_ollama_v1.jsonl`

**Caution:** Ollama gloss-assist + gematria index — **not** arXiv DeepNSM HF 1B checkpoint. 100-pair pilot scope; 500-pair full audit TBD.

**Still HOLD:** `send_gate: HOLD` · `track_a_promotion_forbidden: true`.

---

## Phase 14 — 500-pair Ollama full audit + stub vs Ollama A/B (2026-06-21)

**Command:** `py scripts/run_logos_graphrag_phase14_deepnsm_hf_ollama_500_chain_v1.py` · exit **0**

| Arm | prime_hit | distortion | gate_ok | Notes |
|-----|-----------|------------|---------|-------|
| gematria shadow | **97.9%** | **1.4%** | true | translit index ref |
| gloss-stub (500) | **98.13%** | **1.64%** | true | offline heuristic |
| **Ollama (500)** | **98.13%** | **1.17%** | true | `gemma4:e2b` gloss-assist |
| Δ Ollama−stub | 0pp | **−0.47pp** | — | operational compare |
| Δ Ollama−gematria | **+0.23pp** | **−0.23pp** | — | vs shadow ref |

| Check | Result |
|-------|--------|
| Ollama calls / failures | **500 / 0** |
| avg latency | **0.66s** |
| stub vs Ollama A/B | **ready** |
| Phase 13/12 carry | **true** |
| GATE_SPEC phase | **14** |

**Artifacts:** `reports/logos_graphrag_phase14_deepnsm_hf_ollama_500_chain_v1_latest.json` · `reports/deepnsm_hf_explication_ollama_500_chain_v1_latest.json` · `reports/deepnsm_hf_stub_vs_ollama_500_ab_v1_latest.json`

**Caution:** Ollama gloss-assist — **not** arXiv DeepNSM HF 1B weights. prime_hit tie at 98.13%; distortion edge only.

**Still HOLD:** `send_gate: HOLD` · `track_a_promotion_forbidden: true`.

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

# Phase 11-P compress + Layer C
py scripts/run_logos_graphrag_phase11p_compress_layerc_gate_chain_v1.py

# Phase 11-Q compress parity (active report profile)
py scripts/run_logos_graphrag_phase11q_compress_parity_chain_v1.py

# Phase 11-R cost plane + DeepNSM HF stub
py scripts/run_logos_graphrag_phase11r_cost_deepnsm_stub_chain_v1.py

# Phase 11-S HF A/B + evidence + NL sync
py scripts/run_logos_graphrag_phase11s_evidence_nl_sync_chain_v1.py

# Phase 11-T layer stack closure signoff
py scripts/run_logos_graphrag_phase11t_layer_stack_closure_chain_v1.py

# Phase 12 live bundle + public smoke
py scripts/run_logos_graphrag_phase12_live_public_chain_v1.py

# Phase 13 DeepNSM HF Ollama local-weights pilot
py scripts/run_logos_graphrag_phase13_deepnsm_hf_ollama_chain_v1.py

# Phase 14 500-pair Ollama full audit + stub vs Ollama A/B
py scripts/run_logos_graphrag_phase14_deepnsm_hf_ollama_500_chain_v1.py
```

**Related SSOT:** `ROOT_LEXICON_41K_4D_EVOLUTION_LIT_REVIEW_2026-06-21.md` · `LOGOS_GRAPHRAG_4D_OLLAMA_LIT_REVIEW_2026-06-21.md`
