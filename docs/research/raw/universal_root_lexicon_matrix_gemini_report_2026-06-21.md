# Tier 0 raw — Universal Root Lexicon Matrix (Gemini Deep Research output)

- generated_at_utc: 2026-06-21
- lane: Track B `[HYPO]`
- send_gate: HOLD
- tier: 0 (raw external synthesis — **not Fact-Lock validated**)
- prompt_ssot: `docs/research/raw/universal_root_lexicon_matrix_gemini_prompt_v1.md`
- adversarial_filter: `docs/research/UNIVERSAL_ROOT_LEXICON_MATRIX_LIT_REVIEW_2026-06-21.md` §「Gemini Tier-0 adversarial filter」

---

## MKM staff verdict (one screen)

| Claim in Gemini report | Fact-Lock |
|------------------------|-----------|
| NSM 65 **perfect orthogonality** / column-disjoint matrix | **Reject** — soft gating only |
| **Replace** 41k lemma anchor with universal matrix | **Reject** — Layer A/B/C coexistence |
| LongMemEval **96.8%**, Mem0/Letta benchmark table | **Unverified** — no MKM reproduce artifact |
| CSR **0.98**, token savings **94.2%** OS-wide | **Reject scope** — shallow router fixture only |
| **MKM Technical Specification v4** on disk | **False** — file not in repo at ingest |
| Wanda/SparseGPT on **lexicon** rows | **Category error** — LLM weight pruning |
| Merkle + local hybrid **blockchain** anchor | **`[HYPO]`** — diff-only Python smoke first |
| English distortion diagnosis (~86%) | **Accept direction** — matches NSM↔41k audit |
| MDL \(L(D,M)\), local SLM router, compound gating score | **Salvage as `[HYPO]`** — Layer A/C templates |

---

## Raw body (Gemini synthesis — abbreviated index)

Gemini produced a long-form report covering:

1. **Information theory vs 41k anchors** — MDL, NSM 65 primes, semantic drift via English mediation
2. **4-step pipeline** — corpus charge extraction, geometric pruning, 4D context gating (S_lex, I_t, R_t, D), Hit@k / Jaccard / routing_oracle_gap metrics
3. **Benchmark table** (Mem0, Letta/MemGPT, OMEGA, ByteRover, SimpleMem vs proposed matrix) — **treat as unsourced until reproduced**
4. **Merkle SHA-256 tenant lexicon integrity** + FSRS/Ebbinghaus active pruning
5. **3-step Core OS roadmap** — SQLite+ONNX, Ollama 4D gating middleware, MCP bridge

Full prose was pasted by commander in chat 2026-06-21. This file is the **indexed raw ingest**; do not cite Gemini percentages in Track A or PUBLIC_FACING copy.

Quantitative claims below are routed through `## Digested facts` for Mastication (table heuristic disabled for duplicates).

## Digested facts

### fact_id: gemini_b3_dual_plane_floor
- metric_name: dual_plane_aligned_rate
- value: 0.5
- unit: ratio
- comparison_arm: MKM_B3_floor
- verification_status: Right
- verification_method: fixture_trusted
- baseline_plane: B3_dual_plane
- artifact_path: reports/universal_root_phase1a_baseline_compare_v1_latest.json
- artifact_field: methods.B3.primary_value
- assertion: gte

### fact_id: mem0_gemini_longmemeval_968_claim
- metric_name: longmemeval_recall
- value: 96.8
- unit: percent
- comparison_arm: Mem0 Gemini table (unsourced)
- arxiv_id: 2504.19413
- verification_status: Unknown

### fact_id: mem0_paper_token_savings_90
- metric_name: token_cost_reduction_pct
- value: 90
- unit: percent
- comparison_arm: Mem0 arXiv 2504.19413 abstract
- arxiv_id: 2504.19413
- verification_status: Unknown

### fact_id: gemini_proposed_matrix_token_942
- metric_name: token_savings_pct
- value: 94.2
- unit: percent
- comparison_arm: Proposed matrix Gemini (no arXiv)
- verification_status: Unknown

---

## Reproduce (MKM validated path)

```powershell
# Phase 11-A — NSM 500-pair + gold re-eval
py scripts/run_logos_graphrag_phase11a_chain_v1.py

# NSM distortion only
py scripts/build_nsm_41k_crosswalk_500_fixture_v1.py
py scripts/run_nsm_41k_lexicon_crosswalk_audit_v1.py --expected-pairs 500
```
