# Candidate Rules Delta (H vs H_ext3) - 2026-03-27

- base_cycle: `command_center_followup_20260327_h`
- new_cycle: `command_center_followup_20260327_h_ext3`
- verdict: `PROMOTION_READY`

## Summary

- rule_count_base: `3`
- rule_count_new: `3`
- added: `0`
- removed: `0`
- changed: `3` (promotion state only)
- score_delta: `0.0`
- promotion_state_changed: `true`

## Blocker Recovery

- hebrew_primary_tokens: `266 -> 1024`
- translation_proxy_ratio: `0.901917 -> 0.718759`

## Promotion State Changes

- `fusion_overlap_tok_עולם`: `PILOT -> CANDIDATE_FOR_PROMOTION`
- `fusion_overlap_tok_כל`: `PILOT -> CANDIDATE_FOR_PROMOTION`
- `fusion_overlap_tok_אל`: `PILOT -> CANDIDATE_FOR_PROMOTION`

## Interpretation

The ext3 Hebrew-priority manifest removes the authority blockers and upgrades all exported rules to promotion candidates without score degradation.
