# Candidate Rules Export (command_center_followup_20260327_h_ext3)

- conversion_rules_version: `2026-03-27`
- cycle_tag: `command_center_followup_20260327_h_ext3`
- authority_readiness: `READY`
- default_promotion_state: `CANDIDATE_FOR_PROMOTION`

## Score Snapshot

- pilot_score: `0.609673`
- avg_confidence: `0.675`
- weighted_overlap_factor: `0.43478`
- rule_count_factor: `0.8`

## Blocker Metrics (Recovered)

- hebrew_primary_tokens: `1024`
- translation_proxy_ratio: `0.718759`
- fusion_overlap_ratio_dss: `0.043478`

## Exported Rules

1) rule_id: `fusion_overlap_tok_עולם`
- trigger_token: `עולם`
- action: `apply_in_next_full_eval`
- score: `1.0`
- priority: `1`
- promotion_state: `CANDIDATE_FOR_PROMOTION`
- risk: `low`

2) rule_id: `fusion_overlap_tok_כל`
- trigger_token: `כל`
- action: `stage_ab_eval`
- score: `0.55274`
- priority: `2`
- promotion_state: `CANDIDATE_FOR_PROMOTION`
- risk: `medium`

3) rule_id: `fusion_overlap_tok_אל`
- trigger_token: `אל`
- action: `watchlist_only`
- score: `0.513699`
- priority: `3`
- promotion_state: `CANDIDATE_FOR_PROMOTION`
- risk: `low`

## Execution Hand-off

`py scripts/run_fusion_intake_cycle.py --workload full_eval --skip-sync`
