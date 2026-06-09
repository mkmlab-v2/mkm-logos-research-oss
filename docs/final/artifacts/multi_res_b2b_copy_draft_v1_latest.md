# Multi-Resolution Context Index — B2B draft v1

**Status:** internal · `research_only` · `[HYPO]` · not for external send without legal review  
**Checklist:** `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` v1.7

## One-liner (allowed framing)

MKM can inject **low-resolution operational anchors** first, then expand to **high-resolution evidence** on demand — reducing token cost in agent workflows without claiming identical answer quality.

## What we measure (artifact-backed)

- Ops memory inject scope: ~99.43% token reduction vs full anchor slices (`mkm_ops_memory_index_token_bench_v1_latest.json`)
- Fills multi-res index: daily buckets + row pointers (`multi_res_fills_index_v1_latest.json`)
- Fused bench: combined low-res inject footprint (`multi_res_fusion_bench_v1_latest.json`)

## What we do not claim

- Not “hallucination eliminated” or “perfect integrity”
- Not Track A compression KPI or live trading performance
- Not equivalence between low-res inject and full high-res replay

## Limitations

- B-track only; human sign-off for production promotion
- Quality tradeoffs possible (retrieval Jaccard may decrease vs full gate JSON)
