# Blind Replay C1 Artifact Bundle (2026-04-02)

## Scope
- Phase C.1 feature expansion artifacts for B-track blind replay.
- Exploratory only (`exploratory_only: true`, `a_track_binding_forbidden: true`).

## Canonical Paths
1. `C:\workspace\docs\final\artifacts\BLIND_REPLAY_PROXY_PROFILE_D_PARAMS_V1.json`
2. `C:\workspace\docs\final\artifacts\BLIND_REPLAY_PROXY_PROFILE_D_ENSEMBLE_SEARCH_V1.json`
3. `C:\workspace\docs\final\artifacts\aegis_unified_scoreboard_abcds_latest.json`
4. `C:\workspace\reports\constitution\btrack_pilot\blind_replay\blind_replay_dataset_grid_btc_s80_latest.json`
5. `C:\workspace\reports\constitution\btrack_pilot\blind_replay\blind_replay_dataset_grid_kospi_s80_latest.json`

## Key Results
- Tuning best (`D params`): `unified_score_balanced = 0.373955`
- Ensemble best (`D blend`): `unified_score_balanced = 0.382159`
- Promotion: `PROMOTED = true`
- Unified ace: `profile = D`
- Unified score (7:3, kappa 0.15): `unified_bal_7_3 = 0.382159`

## Extended Validation (BTC 90 / Kappa 0.10)
- Artifact: `C:\workspace\docs\final\artifacts\aegis_unified_scoreboard_btc90_k010_latest.json`
- Real re-run result: `unified_score_balanced = 0.40342`
- Prior baseline (7:3, kappa 0.15): `0.382159`
- Delta: `+0.021261`
- Ace profile remains: `D`

## Notes
- This bundle is for NotebookLM indexing and ops traceability.
- Runtime vault mirror sync completed in local ops log (`copied=51`, `skipped=7 optional`).
