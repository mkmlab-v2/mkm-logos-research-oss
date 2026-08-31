# MKM Governance Ablation N80+ — post-freeze staging checklist v1

**Status:** B-track · `send_gate: HOLD` · `GOVERNANCE_SUPERIORITY: NOT_ESTABLISHED`

## Current gate

`WAIT_FOR_PRIMARY_BLIND_HUMAN_172_OF_172_FREEZE`

Verify:

```powershell
py scripts/check_mkm_governance_ablation_n80plus_primary_blind_freeze_v1.py
```

Exit **0** + `01_PRIMARY_BLIND_FREEZE_RECEIPT.json` with `primary_blind_freeze_complete: true` required before unblind staging.

## Pre-freeze (already committed in ae82374a7)

- `HUMAN_RATER_PROTOCOL_v1.md`
- `HUMAN_RATER_QUICK_GUIDE_v1.md`
- `rater1/2/3_input_v1.csv` (blank score cells OK until freeze)
- `00_BLINDING_RECEIPT.json`

**Never stage before freeze:**

- `rater_key_hidden_v1.json`
- `rater_worksheet_v1.json`
- `response_archive/arm_a/**`, `response_archive/arm_b/**`
- `secondary_ai_review/**`
- `01_RESULT_SEAL_RECEIPT.json`, `PAIRED_AB_LEDGER.jsonl`
- automatic scorer / critical queue artifacts

## Post-freeze phases (sequential)

### Phase 1 — UNBLIND-ELIGIBLE ARCHIVE

After freeze receipt OK:

```powershell
git add docs/research/mkm_governance_ablation_n80plus/response_archive/
git add docs/research/mkm_governance_ablation_n80plus/blind_human_rater/rater_worksheet_v1.json
git add docs/research/mkm_governance_ablation_n80plus/blind_human_rater/01_PRIMARY_BLIND_FREEZE_RECEIPT.json
git add docs/research/mkm_governance_ablation_n80plus/PAIRED_AB_LEDGER.jsonl
py scripts/check_mkm_governance_ablation_n80plus_post_freeze_staging_v1.py --require-freeze-receipt
```

### Phase 2 — SECONDARY AI ARCHIVE

Only after Phase 1 commit:

```powershell
git add docs/research/mkm_governance_ablation_n80plus/blind_human_rater/secondary_ai_review/
py scripts/check_mkm_governance_ablation_n80plus_post_freeze_staging_v1.py --require-freeze-receipt
```

### Phase 3 — RESULT SEAL PACKAGE

After human adjudication ACK:

```powershell
git add docs/research/mkm_governance_ablation_n80plus/01_RESULT_SEAL_RECEIPT.json
git add docs/research/mkm_governance_ablation_n80plus/blind_human_rater/rater_key_hidden_v1.json
git add docs/research/mkm_governance_ablation_n80plus/blind_human_rater/02_HUMAN_RATER_RESULT_RECEIPT.json
```

## Always before commit

```powershell
git diff --cached --name-only
py scripts/check_mkm_governance_ablation_n80plus_post_freeze_staging_v1.py
```

Forbidden pattern count must be **0** unless `--require-freeze-receipt` phase allows it.

## Push / promotion

`push / promotion / unblind = HOLD` until commander ACK per phase.
