# Map-Factory PoC v1 — IC 10-Sentence Brief (Fact-Safe, EN)

1. The PoC goal is not universal text compression, but validating lossless reconstruction and simulated efficiency on B2B boilerplate-heavy domains.  
2. The source of truth is `docs/final/artifacts/comparison_summary_latest.json`, and all numbers in this brief are grounded in that artifact.  
3. Batch integrity is confirmed by `integrity_guarantee_flag=true` and `decode_check_ok=true` for included runs.  
4. In KJV/NIV/ESV cross-evaluation, in-map aligned inputs show `match_rate_by_utf8_octet` around `0.69~0.74`, while cross-map hits are `0.0`.  
5. Across three business domains (`it_terms`, `finance_terms`, `api_policy`), aligned eval average is `aligned_eval_a_avg_match_rate_by_utf8_octet=0.6217916`.  
6. Non-aligned eval and KJV cross baseline remain zero-hit, reported as `negative_eval_b_all_zero_hit=true` and `kjv_cross_baseline_all_zero_hit=true`.  
7. Auto-map routing uses thresholded decisions: aligned inputs route to `map_selected`, and zero-hit inputs downgrade to `fallback_verbatim_only` (see `auto_map_probe`).  
8. Threshold sweep (`0.01/0.03/0.05/0.1`) shows stable behavior: 3 aligned domain inputs stay selected, while 1 non-aligned arXiv input stays fallback (`docs/final/artifacts/auto_map_threshold_sweep_latest.json`).  
9. Mixed-domain documents (api+finance) expose the current single-map limitation: each map optimizes only its own spans and leaves non-matching spans as verbatim (`mixed_api_finance_probe`).  
10. All efficiency values are `premises`-based bit-simulation observations, and must not be claimed as guaranteed billing, wire-byte, or VRAM reduction without separate measurement and contractual validation.
