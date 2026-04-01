# MKM TOE Paper Trading Gate

- generated_at_utc: 2026-04-01T12:36:47Z
- decision: PASS

## Policy
- allowed_model: dl_candidate_mlp_only
- auto_downgrade_to_hold_if_any_fail: true
- weekly_retrain_required: true
- execution_mode: paper_trading_only

## Checks
- stage2_pass: True
- audit_pass: True
- mlp_pass_candidate: True
- mlp_r2_gte_0: True
- mlp_mae_lte_0_25: True

## Metrics Snapshot
- mlp_mae: 0.166102
- mlp_r2: 0.035018

## Next Action
- Enable paper trading gate with MLP-only policy.
