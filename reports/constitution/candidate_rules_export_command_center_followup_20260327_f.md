# Candidate Rules Export (command_center_followup_20260327_f)

- conversion_rules_version: `2026-03-27`
- cycle_tag: `command_center_followup_20260327_f`
- authority_readiness: `BLOCKED`
- default_promotion_state: `PILOT`

## Score Snapshot

- pilot_score: `0.609673`
- avg_confidence: `0.675`
- weighted_overlap_factor: `0.43478`
- rule_count_factor: `0.8`

## Blocking Reasons

- `hebrew_primary_below_threshold`
- `high_translation_proxy_ratio`
- `insufficient_hebrew_primary_tokens`
- `translation_proxy_ratio_above_threshold`

## Exported Rules

1) rule_id: `fusion_overlap_tok_עולם`
- trigger_token: `עולם`
- action: `apply_in_next_full_eval`
- score: `1.0`
- priority: `1`
- promotion_state: `PILOT`
- risk: `low`
- evidence:
  - `projects/dss-4d-ingest/outputs/fusion_rule_candidates_command_center_followup_20260327_f.json`
  - `projects/dss-4d-ingest/outputs/fusion_rule_candidate_score_command_center_followup_20260327_f.json`
  - `reports/constitution/dss_insight_priority_latest.json`

2) rule_id: `fusion_overlap_tok_כל`
- trigger_token: `כל`
- action: `stage_ab_eval`
- score: `0.55274`
- priority: `2`
- promotion_state: `PILOT`
- risk: `medium`
- evidence:
  - `projects/dss-4d-ingest/outputs/fusion_rule_candidates_command_center_followup_20260327_f.json`
  - `projects/dss-4d-ingest/outputs/fusion_rule_candidate_score_command_center_followup_20260327_f.json`
  - `reports/constitution/dss_insight_priority_latest.json`

3) rule_id: `fusion_overlap_tok_אל`
- trigger_token: `אל`
- action: `watchlist_only`
- score: `0.513699`
- priority: `3`
- promotion_state: `PILOT`
- risk: `low`
- evidence:
  - `projects/dss-4d-ingest/outputs/fusion_rule_candidates_command_center_followup_20260327_f.json`
  - `projects/dss-4d-ingest/outputs/fusion_rule_candidate_score_command_center_followup_20260327_f.json`
  - `reports/constitution/dss_insight_priority_latest.json`

## Execution Hand-off

`py scripts/run_dss_insight_priority_cycle.py --max-actions 1`
