# MKM Governance Ablation N80+ — Blind Human Rater Protocol v1

**ACK:** `COMMANDER_MKM_GOVERNANCE_ABLATION_N80PLUS_BLIND_HUMAN_RATING_COLLECTION_ACK`  
**Scope:** sealed 172-response archive independent rescoring  
**N responses:** 172  
**Primary evidence ceiling:** blind human rater scores only — not secondary AI review

## Rater instructions

1. Score **only** from the rater worksheet / CSV — do **not** open `rater_key_hidden_v1.json` until all ratings are frozen.
2. Do **not** consult automatic scorer outputs or `mkm_governance_ablation_n80plus_result_seal_v1_latest.json`.
3. Do **not** consult `secondary_ai_review/` (scores, notes, provenance, audit queues). Secondary AI is **post-rating adjudication support only** — exposing critical/mismatch queues to raters contaminates blind independence.
4. Each row = one blind response (`blind_label`). ARM identity is hidden.
5. Use frozen per-item rubric fields in the worksheet (`scoring_rubric`, `authority_ceiling_boundary`, `critical_error_conditions`).
6. Binary fields: `0` = absent/false, `1` = present/true. `appropriate_abstention`: `0`/`1`/`NA`.
7. **critical error (derived):** any of false_claim, unsupported_claim, ceiling_violation, citation_error, authority_overreach = 1.
8. Minimum **2 independent raters**; **3 raters** preferred. Save one CSV per rater.
9. Score **all 172 rows** in blind order — no “priority subset” from any prior review lane.

## Scoring dimensions

`false_claim, unsupported_claim, ceiling_violation, citation_error, authority_overreach, appropriate_abstention, useful_answer, gold_alignment`

## Adjudication (pre-specified)

- 3 raters: majority vote per dimension; ties → `ADJUDICATION_REQUIRED`.
- 2 raters: unanimous else `ADJUDICATION_REQUIRED` (commander tie-break).
- Do **not** drop or edit questions after rating.
- Do **not** tune thresholds post-hoc.

## Forbidden

- Model rerun / response regeneration
- Q-bank / gold / rubric mutation
- Superiority / SEND / product DONE / Track A claims from human scores alone
- Merging pilot N30 with N80+ as same-model replication
- Sharing secondary AI critical/mismatch audit queues with raters before scoring completes
- Showing raters other raters’ scores or ARM identity

## After scoring

```powershell
py scripts/aggregate_mkm_governance_ablation_n80plus_blind_human_scores_v1.py
py scripts/check_mkm_governance_ablation_n80plus_blind_human_rater_result_v1.py
```
