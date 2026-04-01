# MKM TOE Stage2 Model Compare

## 3-line summary
1) Stage2 compare executed at 2026-04-01T12:36:45Z.
2) Decision: PASS (stage2_candidate_ready).
3) This is model-screening evidence, not deterministic performance guarantee.

## Dataset
- path: C:\workspace\docs\final\artifacts\mkm_toe_training_dataset_v3.csv
- sample_count_supervised: 24
## xgboost_baseline
- fit_mode: chronological_oos
- mse: 0.118406
- mae: 0.293788
- r2: -1.431631
## dl_candidate_mlp
- fit_mode: chronological_oos
- mse: 0.046989
- mae: 0.166102
- r2: 0.035018

## Limitation
- Current sample is small; out-of-sample reliability must be re-validated on expanded window.
- Report is probabilistic and evidence-bound.

## Next action
- If PASS, proceed to controlled paper-trading gate; if HOLD, expand data and recalibrate.
