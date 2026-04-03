# Logos Shadow 202003 Insight Brief v1

**schema**: `logos_shadow_insight_brief_v1`  
**mode**: `OBSERVATION_ONLY`  
**generated_at_utc**: `2026-04-03T12:10:33Z`  
**source_result**: `reports/research/logos_shadow_v1/logos_kospi_shadow_202003_v1_latest.json`

## Scope

- Period: `2019-10-01` ~ `2020-05-29`
- Cycle priority: `40 -> 7 -> 50`
- Crash definition: 20-day rolling peak, trigger if drop <= `-10%` within 5 days
- Lens source: `docs/final/artifacts/logos_independent_lens_latest.json`

## Core Metrics

- `hit_direction_rate`: `0.0`
- `crash_warning_recall`: `1.0`
- `warnings_count`: `102`
- `crash_event_count`: `5`
- `direction_sign_from_lens`: `neutral`
- `direction_score_from_lens`: `0.0`
- `confidence_from_lens`: `0.2`

## Threshold Sweep (v1)

- Sweep report: `reports/research/logos_shadow_v1/logos_kospi_shadow_threshold_sweep_latest.json`
- Tested configs: `5`
- Top-ranked config by raw hit/recall:
  - `drawdown=-0.06`, `cycle=0.12`, `warn=0.18`, `down=0.16`
  - `hit_direction_rate=0.633028`, `crash_warning_recall=1.0`, `warnings_count=113`
- Conservative candidate (lower warning volume):
  - `drawdown=-0.07`, `cycle=0.20`, `warn=0.28`, `down=0.22`
  - `hit_direction_rate=0.075`, `crash_warning_recall=1.0`, `warnings_count=40`

### Sweep Interpretation Guard

- High hit-rate with very high warning count can reflect permissive thresholds and class imbalance.
- Promotion decisions must prefer stable behavior across additional windows, not single-window peak score.
- Keep `OBSERVATION_ONLY` until out-of-window validation and baseline comparison are added.

## Cross-Window Validation (v1)

- CV report: `reports/research/logos_shadow_v1/logos_kospi_shadow_cv_windows_latest.json`
- Windows:
  - `w1_2019_q4` (`2019-10-01` ~ `2019-12-31`)
  - `w2_2020_q1_crash` (`2020-01-01` ~ `2020-03-31`)
  - `w3_2020_q2_rebound` (`2020-04-01` ~ `2020-05-29`)
- Per-window best (same winner):
  - `drawdown=-0.06`, `cycle=0.12`, `warn=0.18`, `down=0.16`
  - Q1 crash: `hit_direction_rate=0.488889`, `crash_warning_recall=1.0`, `warnings_count=50`
  - Q4/Q2: `crash_event_count=0` so recall is structurally `0.0`; high hit rates are not directly comparable to crash-window utility.

### CV Interpretation Guard

- Single-window peak scores overstate generalization risk.
- Crash-window utility should prioritize `crash_warning_recall` and stable warning volume first, then direction hit.
- Keep this lens in `OBSERVATION_ONLY` until additional non-synthetic windows and baseline deltas are accumulated.

## External Proxy Validation (monthly OHLCV)

- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_cv_external_proxy_latest.json`
- Source: `reports/constitution/btrack_pilot/blind_replay/kospi_proxy_ohlcv_from_training_result.csv`
- Source range: `1997-01-01` ~ `2005-04-01` (monthly proxy; not full modern span)
- Windows tested:
  - `w4_1997_asia_crisis_proxy_monthly` (24 rows)
  - `w5_2000_dotcom_stress_proxy_monthly` (24 rows)
- Best config across both windows remains:
  - `drawdown=-0.06`, `cycle=0.12`, `warn=0.18`, `down=0.16`
- Key metrics:
  - 1997 crisis proxy: `hit_direction_rate=0.117647`, `crash_warning_recall=1.0`, `warnings_count=22`
  - 2000 stress proxy: `hit_direction_rate=0.157895`, `crash_warning_recall=0.75`, `warnings_count=24`

### External Proxy Guard

- This is monthly proxy OHLCV, not tick/daily exchange feed.
- Use this only as robustness evidence for threshold stability, not as production efficacy proof.

## External Daily Validation (yfinance)

- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_cv_external_daily_latest.json`
- Source: `research/market_data/kospi_daily_external_yf.csv` (`^KS11`, rows=`4685`)
- Windows tested:
  - `w6_2008_gfc_daily` (`2008-01-01` ~ `2009-03-31`, rows=309)
  - `w7_2020_covid_daily` (`2019-12-01` ~ `2020-06-30`, rows=143)
- Best config in both windows:
  - `drawdown=-0.06`, `cycle=0.12`, `warn=0.18`, `down=0.16`
- Key metrics:
  - 2008 window: `hit_direction_rate=0.258216`, `crash_warning_recall=1.0`, `warnings_count=216`
  - 2020 window: `hit_direction_rate=0.378947`, `crash_warning_recall=1.0`, `warnings_count=96`

### External Daily Guard

- Crash recall is stable (`1.0`) but warning volume is high, so precision/operational burden is still unresolved.
- Keep `OBSERVATION_ONLY`; treat this as generalization evidence, not direct promotion trigger.

## Precision/Load Tuning v2

- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_tuning_v2_latest.json`
- Objective: `2.0*recall + precision - 1.3*load`
- Candidate grid: `81` configs (external daily windows: 2008 + 2020)
- Top objective family:
  - representative config: `drawdown=-0.07`, `cycle=0.12`, `warn=0.22`, `down=0.16`
  - aggregate: `avg_recall=0.977272`, `avg_precision=0.128572`, `avg_load_ratio=0.37339`
  - objective score: `1.59771`

### Tuning Guard

- v2 improves precision/load trade-off relative to high-warning settings, but warning burden is still non-trivial.
- Keep this as research candidate set; promotion requires additional precision-focused baselines.

## Precision/Load/False-Alert Tuning v3

- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_tuning_v3_top3_latest.json`
- Objective: `2.0*recall + precision - 0.9*load - 1.1*false_alert_density`
- Winner:
  - `drawdown=-0.07`, `cycle=0.12`, `warn=0.22`, `down=0.16`
  - `avg_recall=0.977272`, `avg_precision=0.128572`, `avg_load_ratio=0.37339`, `avg_false_alert_density=0.117173`
  - `objective_v3=1.618176`

### v3 Guard

- False-alert penalty improves candidate ranking fidelity, but absolute warning burden remains high.
- Keep `OBSERVATION_ONLY` and treat v3 winner as the current research baseline only.

## False-Alert Benchmark (Calm-biased windows)

- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_false_alert_benchmark_latest.json`
- Fixed config: `drawdown=-0.07`, `cycle=0.12`, `warn=0.22`, `down=0.16` (v3 winner)
- Windows tested:
  - `w8_2017_calm_daily`: `false_alert_density=0.091286`, `warning_load_ratio=0.091286`
  - `w9_2013_calm_daily`: `false_alert_density=0.089069`, `warning_load_ratio=0.105263`
- Aggregate:
  - `avg_false_alert_density_calm=0.090177`
  - `avg_warning_load_ratio_calm=0.098275`
  - proposed cap (`+15% buffer`): `false_alert_density <= 0.103704`

### False-Alert Guard

- Window `w9_2013_calm_daily` still contains 2 crash events, so this is calm-biased rather than pure no-crash.
- Use `0.103704` as provisional cap; finalize only after adding one strictly no-crash reference window.

## False-Alert Gate v4 (Strict no-crash)

- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_false_alert_gate_v4_latest.json`
- Auto-selected strict no-crash year (external daily):
  - `w10_2017_strict_no_crash_daily` (`rows=241`, `min_drawdown_year=-0.05377`)
- Config tested: `drawdown=-0.07`, `cycle=0.12`, `warn=0.22`, `down=0.16`
- Result:
  - `false_alert_density=0.091286`
  - provisional cap `0.103704` 대비 **PASS**
  - decision: `OBSERVATION_ONLY_BASELINE_VALID`

### v4 Guard

- PASS means baseline validity in research mode only; it is not a production promotion signal.
- Keep `OBSERVATION_ONLY` until precision and warning-load objectives are explicitly tied to downstream cost constraints.

## Cost Gate v5 (precision-load-cost)

- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_cost_gate_v5_latest.json`
- Input winner config: `drawdown=-0.07`, `cycle=0.12`, `warn=0.22`, `down=0.16`
- Cost model (initial):
  - `warning_review_minutes=6.0`
  - `review_cost_per_minute=0.8`
  - `false_alert_penalty_units=1.5`
- Result:
  - `cost_efficiency_score=0.043319`
  - `min_cost_efficiency_score=0.35`
  - gate decision: `OBSERVATION_ONLY_COST_BLOCKED` (**PASS 아님**)

### v5 Guard

- Under current cost assumptions, warning burden dominates precision gain.
- Keep this gate blocked and continue threshold/model tuning before any promotion discussion.

## v6 Sparsification (cluster + refractory)

- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_sparsification_v6_latest.json`
- Base config: `drawdown=-0.07`, `cycle=0.12`, `warn=0.22`, `down=0.16`
- Variants tested: `(10,10)`, `(7,7)`, `(5,5)` as `(cluster_merge_days, refractory_days)`
- Winner: `(10,10)`
  - `avg_recall=0.495455`
  - `avg_precision=0.357143`
  - `avg_load_ratio=0.025313`
  - `avg_false_alert_density=0.013726`
  - `cost_efficiency_score=0.31271` (**still below 0.35**)

### v6 Guard

- Sparsification sharply reduces load and false-alert density, but recall drops materially.
- Cost gate remains blocked (`pass_cost_gate=false`), so maintain `OBSERVATION_ONLY`.

## v7 Adaptive Sparsification (crisis-aware refractory)

- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_sparsification_v7_latest.json`
- Base: v6 winner + adaptive override (`crisis_relax_drawdown`, `crisis_refractory_days`)
- Tested variants:
  - `(-0.12, 3)`, `(-0.10, 2)`, `(-0.09, 1)`, `(-0.08, 1)`
- Result:
  - All variants converged to the same metrics as v6 winner
  - `cost_efficiency_score=0.31271`, `pass_cost_gate=false`

### v7 Guard

- In current signal geometry, crisis-aware refractory did not recover recall without re-inflating cost.
- Keep `OBSERVATION_ONLY`; next improvement requires signal model change, not sparsification policy only.

## v8 Signal-Model Update (front-end scoring change)

- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_sparsification_v8_latest.json`
- Approach:
  - Added calm-regime penalty to cycle contribution (`effective_cycle_resonance`)
  - Added stress gate for cycle-driven warnings (`cycle_stress_min`)
  - Kept v6/v7 sparsification shell (`cluster=10`, `refractory=10`, crisis override)
- Sweep size: 27 variants on external daily windows (2008 GFC, 2020 COVID)
- Winner:
  - `cycle_stress_min=0.01`
  - `calm_vol_window=10`
  - `calm_vol_threshold=0.01`
  - `calm_cycle_penalty=0.08`
- Winner metrics:
  - `avg_recall=0.318182`
  - `avg_precision=0.416666`
  - `avg_load_ratio=0.016702`
  - `avg_false_alert_density=0.006993`
  - `cost_efficiency_score=0.382033`
  - `pass_cost_gate=true`

### v8 Guard

- Cost gate crossed (`0.382 > 0.35`) with lower load/false-alert density.
- Cross-window asymmetry remains: 2008 window strong, 2020 window weak recall in this configuration.
- Maintain `OBSERVATION_ONLY` and require additional stress-window validation before any production binding.

## v9 Dynamic Crisis Warn Threshold

- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_sparsification_v9_latest.json`
- Approach:
  - Added crisis-only dynamic warn threshold in front-end signal stage:
    - `crisis_warn_drawdown`
    - `crisis_composite_warn_threshold`
  - Goal: recover 2020 recall while keeping v8 cost-gate pass.
- Sweep size: 12 variants
- Winner:
  - `crisis_warn_drawdown=-0.10`
  - `crisis_composite_warn_threshold=0.18`
- Winner metrics:
  - `avg_recall=0.318182`
  - `avg_precision=0.416666`
  - `avg_load_ratio=0.016702`
  - `avg_false_alert_density=0.006993`
  - `cost_efficiency_score=0.382033`
  - `pass_cost_gate=true`

### v9 Guard

- Dynamic crisis warn threshold did not move the frontier; metrics remained identical to v8 winner.
- Interpretation: bottleneck is likely in direction/label alignment for 2020 regime, not warn-threshold sensitivity.

## v10 Momentum Regime Patch

- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_sparsification_v10_latest.json`
- Approach:
  - Added momentum feature (`recent_momentum`) to front-end composite score
  - Added momentum-trigger warning gate (`momentum_warn_threshold`)
  - Goal: recover 2020 recall while preserving v8/v9 cost-gate pass
- Sweep size: 27 variants
- Winner:
  - `momentum_window=5`
  - `momentum_weight=0.15`
  - `momentum_warn_threshold=0.01`
- Winner metrics:
  - `avg_recall=0.204545`
  - `avg_precision=0.5`
  - `avg_load_ratio=0.016962`
  - `avg_false_alert_density=0.012108`
  - `cost_efficiency_score=0.45472`
  - `pass_cost_gate=true`

### v10 Guard

- Cost efficiency improved materially, but recall deteriorated versus v8/v9.
- 2020 window recall remains `0.0`; bottleneck persists in crisis-event capture, not cost shaping.
- Keep `OBSERVATION_ONLY`; prioritize recall-focused regime features before any live binding discussion.

## v11 Shock + Label Regime Patch

- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_sparsification_v11_latest.json`
- Approach:
  - Added short-horizon shock feature (`recent_shock`) to front-end composite
  - Added shock-trigger warning gate (`shock_warn_threshold`)
  - Exposed crash label knobs (`crash_horizon`, `crash_drop_threshold`) for regime-aware calibration
- Sweep size: 108 variants
- Winner:
  - `shock_window=2`
  - `shock_weight=0.15`
  - `shock_warn_threshold=0.02`
  - `crash_horizon=5`
  - `crash_drop_threshold=-0.10`
- Winner metrics:
  - `avg_recall=0.404546`
  - `avg_precision=0.425`
  - `avg_load_ratio=0.023695`
  - `avg_false_alert_density=0.015344`
  - `cost_efficiency_score=0.373873`
  - `pass_cost_gate=true`

### v11 Guard

- v10 대비 recall이 복구되었고(특히 2020 recall `0.0 -> 0.4`), cost gate pass를 유지했다.
- 정밀도는 v10 최고치(0.50) 대비 일부 낮아졌지만, cross-window 균형 관점에서는 v11이 우위.
- Continue `OBSERVATION_ONLY`; next step is out-of-window holdout to confirm stability.

## v12 Holdout Validation (out-of-window)

- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_holdout_v12_latest.json`
- Fixed params: v11 winner set
- Holdout windows:
  - `h1_2011_euro_daily`
  - `h2_2015_cn_deval_daily`
  - `h3_2018_q4_riskoff_daily`
  - `h4_2022_rate_shock_daily`
- Aggregate:
  - `avg_recall=0.666667`
  - `avg_precision=0.4`
  - `avg_load_ratio=0.022705`
  - `avg_false_alert_density=0.014531`
  - `cost_efficiency_score=0.353737`
  - `pass_cost_gate=true`

### v12 Guard

- Holdout aggregate passes cost gate, but margin is thin (`0.3537` vs `0.35`).
- Window variance remains meaningful (e.g., 2011 precision low), so stability is not yet fully settled.
- Keep `OBSERVATION_ONLY`; require one additional robustness pass before discussing any promotion.

## v13 Robustness Pass (bootstrap + calm-only stress)

- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_robustness_v13_latest.json`
- Fixed params: v11 winner set
- Method:
  - Bootstrap on holdout core windows (`B=200`, sample-with-replacement)
  - Calm-only stress windows to test false-alert resilience
- Core aggregate (same as v12 baseline):
  - `cost_efficiency_score=0.353737`
  - `pass_cost_gate=true`
- Calm-only aggregate:
  - `avg_recall=0.0`
  - `avg_precision=0.309524`
  - `avg_load_ratio=0.028743`
  - `avg_false_alert_density=0.028743`
  - `cost_efficiency_score=0.262068`
  - `pass_cost_gate=false`
- Bootstrap summary:
  - `pass_rate=0.53`
  - `cost_efficiency q05/q50/q95 = 0.140825 / 0.353737 / 0.489732`

### v13 Guard

- Robustness is insufficient for promotion: calm-regime false alerts remain a structural weakness.
- With only 53% bootstrap pass rate, current setup is too close to the decision boundary.
- Maintain `OBSERVATION_ONLY`; prioritize calm-regime suppression in next iteration.

## v14 Calm-Regime Hard Suppression

- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_robustness_v14_latest.json`
- Approach:
  - Added hard suppress gate in warning stage for calm regime:
    - `calm_hard_suppress_vol_threshold`
    - `calm_hard_suppress_shock_threshold`
    - `calm_hard_suppress_drawdown_floor`
  - Evaluated 27 variants with robustness priority:
    - calm pass -> bootstrap pass rate -> core objective
- Winner:
  - `calm_hard_suppress_vol_threshold=0.008`
  - `calm_hard_suppress_shock_threshold=0.018`
  - `calm_hard_suppress_drawdown_floor=0.025`
- Winner robustness:
  - Core aggregate:
    - `avg_recall=0.677083`
    - `avg_precision=0.641667`
    - `avg_load_ratio=0.018641`
    - `avg_false_alert_density=0.011491`
    - `cost_efficiency_score=0.579797`
    - `pass_cost_gate=true`
  - Calm aggregate:
    - `avg_recall=0.0`
    - `avg_precision=0.5`
    - `avg_load_ratio=0.020445`
    - `avg_false_alert_density=0.020445`
    - `cost_efficiency_score=0.442948`
    - `pass_cost_gate=true`
  - Bootstrap:
    - `trials=120`
    - `pass_rate=0.991667`
    - `q05_cost_eff=0.399596`

### v14 Guard

- Robustness improved materially; calm-regime failure mode is now controlled under this protocol.
- Despite strong numbers, keep `OBSERVATION_ONLY` until one independent temporal split confirms no hidden leakage/regime overfit.

## v15 Independent Temporal Split Validation

- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_temporal_generalization_v15_latest.json`
- Fixed params: v14 winner set
- Temporal splits:
  - `t1_2003_2007_pre_gfc`
  - `t2_2010_2014_post_gfc`
  - `t3_2023_2024_recent`
- Aggregate:
  - `avg_recall=0.132576`
  - `avg_precision=0.354545`
  - `avg_load_ratio=0.021005`
  - `avg_false_alert_density=0.019789`
  - `cost_efficiency_score=0.313617`
  - `pass_cost_gate=false`

### v15 Guard

- v14 robustness does not generalize across independent temporal splits.
- Recent window (`2023-2024`) recall is `0.0`, indicating regime-transfer weakness.
- Maintain `OBSERVATION_ONLY`; treat v14 as split-sensitive and require temporal adaptation before promotion discussion.

## v16 Era-Aware Threshold Adaptation

- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_temporal_adaptive_v16_latest.json`
- Approach:
  - Added year-based adaptive thresholds for recent era (`>= recent_era_start_year`)
  - Tuned:
    - `recent_cycle_stress_min`
    - `recent_composite_warn_threshold`
    - `recent_shock_warn_threshold`
- Sweep size: 27 variants on the same temporal splits as v15
- Winner:
  - `recent_cycle_stress_min=0.003`
  - `recent_composite_warn_threshold=0.14`
  - `recent_shock_warn_threshold=0.01`
- Winner aggregate:
  - `avg_recall=0.132576`
  - `avg_precision=0.288889`
  - `avg_load_ratio=0.017596`
  - `avg_false_alert_density=0.01638`
  - `cost_efficiency_score=0.260487`
  - `pass_cost_gate=false`
- Recent window (`2023-2024`) status:
  - `recall=0.0`
  - `precision=0.166667`
  - `warnings_count=6`

### v16 Guard

- Simple era-aware threshold relaxation did not recover recent-regime recall and degraded precision/cost.
- Bottleneck is structural (feature/label mismatch in recent regime), not a threshold-only issue.
- Keep `OBSERVATION_ONLY`; move to regime feature redesign rather than further threshold sweeps.

## v17 Recent-Regime Feature Redesign

- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_recent_feature_v17_latest.json`
- Approach:
  - Added recent-regime dedicated features:
    - `recent_vol_expansion` (short/long volatility expansion)
    - `recent_gap_risk` (negative day-gap proxy from close-to-close jump)
  - Added feature weights and trigger thresholds:
    - `recent_vol_exp_weight`, `recent_gap_weight`
    - `recent_vol_exp_warn_threshold`, `recent_gap_warn_threshold`
- Sweep size: 81 variants on temporal splits (`t1/t2/t3`)
- Winner:
  - `recent_vol_exp_weight=0.15`
  - `recent_gap_weight=0.1`
  - `recent_vol_exp_warn_threshold=0.18`
  - `recent_gap_warn_threshold=0.01`
- Winner aggregate:
  - `avg_recall=0.132576`
  - `avg_precision=0.288889`
  - `avg_load_ratio=0.017596`
  - `avg_false_alert_density=0.01638`
  - `cost_efficiency_score=0.260487`
  - `pass_cost_gate=false`
- Recent window (`2023-2024`) status:
  - `recall=0.0`
  - `precision=0.166667`
  - `warnings_count=6`

### v17 Guard

- Recent-regime feature redesign did not move the frontier versus v16.
- Current close-only input is likely insufficient for recent-regime crash-capture; richer OHLC/volume features are required.
- Keep `OBSERVATION_ONLY`; next iteration should pivot to data-schema upgrade before further threshold/weight sweeps.

## v18 OHLCV Schema Upgrade

- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_ohlcv_upgrade_v18_latest.json`
- Approach:
  - Upgraded signal model to use full OHLCV-derived features:
    - intraday range ratio
    - body ratio
    - volume surge (vs trailing average)
    - gap-open risk proxy
  - Added weighted OHLCV risk term into composite and direct OHLCV trigger gate.
- Sweep size: 243 variants on temporal splits (`t1/t2/t3`)
- Winner:
  - `ohlcv_range_weight=0.04`
  - `ohlcv_body_weight=0.03`
  - `ohlcv_volume_weight=0.04`
  - `ohlcv_gap_open_weight=0.04`
  - `ohlcv_feature_warn_threshold=0.03`
- Winner aggregate:
  - `avg_recall=0.132576`
  - `avg_precision=0.341991`
  - `avg_load_ratio=0.014756`
  - `avg_false_alert_density=0.01354`
  - `cost_efficiency_score=0.313426`
  - `pass_cost_gate=false`
- Recent window (`2023-2024`) status:
  - `recall=0.0`
  - `precision=0.0`
  - `warnings_count=6`

### v18 Guard

- OHLCV feature expansion improved load/false-alert metrics, but failed to recover recent-regime recall.
- Temporal gate still fails; model remains unsuitable for promotion.
- Keep `OBSERVATION_ONLY`; next step should target label ontology and event definition, not additional feature-weight sweeps.

## v19 Label Ontology Redesign (multi-event)

- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_label_ontology_v19_latest.json`
- Approach:
  - Enabled multi-event labeling (`--use-multi-event-labels`) with union events:
    - A) peak-drop crash event (existing)
    - B) down-streak event (`streak_days`, `streak_threshold`)
    - C) volatility-break event (`vol_break_window`, `vol_break_threshold`)
  - Objective: recover recent-regime recall where threshold/feature-only tuning failed.
- Sweep size: 81 variants on temporal splits (`t1/t2/t3`)
- Winner:
  - `streak_days=5`
  - `streak_threshold=-0.05`
  - `vol_break_window=10`
  - `vol_break_threshold=0.018`
- Winner aggregate:
  - `avg_recall=0.312857`
  - `avg_precision=0.341991`
  - `avg_load_ratio=0.014756`
  - `avg_false_alert_density=0.010822`
  - `cost_efficiency_score=0.314601`
  - `pass_cost_gate=false`
- Recent window (`2023-2024`) status:
  - `recall=0.4` (recovered from 0.0)
  - `precision=0.0`
  - `warnings_count=6`
  - `crash_event_count=10`

### v19 Guard

- Label ontology redesign successfully restored recent recall, but precision/cost gate did not recover.
- This indicates recall-precision tradeoff moved, not solved.
- Keep `OBSERVATION_ONLY`; next step should focus on precision recovery for recent-era alerts (e.g., post-filtering/calibration layer).

## v20 Recent-Era Precision Recovery Layer

- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_precision_recovery_v20_latest.json`
- Approach:
  - Tag each alert with `evidence_channels` / `evidence_count` (multi-signal agreement)
  - For `year >= recent_era_start_year`, apply:
    - minimum evidence filter (`recent_precision_min_evidence`)
    - rolling density cap (`recent_precision_density_window`, `recent_precision_density_max`)
- Sweep size: 12 variants on temporal splits (`t1/t2/t3`)
- Winner:
  - `recent_precision_min_evidence=3`
  - `recent_precision_density_window=30`
  - `recent_precision_density_max=1`
- Winner aggregate:
  - `avg_recall=0.279524`
  - `avg_precision=0.341991`
  - `avg_load_ratio=0.012711`
  - `avg_false_alert_density=0.009458`
  - `cost_efficiency_score=0.318072`
  - `pass_cost_gate=false`
- Recent window (`2023-2024`) status:
  - `recall=0.3`
  - `precision=0.0` (directional precision metric remains weak under current definition)

### v20 Guard

- Precision layer reduced load/false-alert density but did not cross the cost gate.
- Recent `warning_precision` still reads `0.0` under the current hit-rate proxy; treat as a metric-definition issue, not only a filter issue.
- Keep `OBSERVATION_ONLY`; next step should revisit evaluation metrics for rare-event warning systems (precision/recall on warnings vs directional hits).

## v21 Metric Separation (direction vs precrash zone)

- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_metrics_separation_v21_latest.json`
- Code fix: `warning_precision` was incorrectly mirrored from `hit_direction_rate`; it now matches **precrash-zone precision** (`precrash_zone_true_count / warnings_count`).
- New fields:
  - `precrash_zone_precision`
  - `warning_false_positive_ratio`
  - `recent_era_precrash_zone_precision` (warnings only when `year >= recent_era_start_year`)
- Payload schema bump: `logos_kospi_shadow_v1_1` (includes `metrics_note`)
- Snapshot aggregate (v20 winner params, temporal splits `t1/t2/t3`):
  - `hit_direction_rate` avg `0.341991` (directional proxy)
  - `precrash_zone_precision` avg `0.284271` (crash-task proxy)
  - `recent_era_precrash_zone_precision` avg `0.111111`

### v21 Guard

- Directional hit rate and precrash precision can diverge; do not use them interchangeably in gates.
- Keep `OBSERVATION_ONLY`; cost-gate formulas that used `warning_precision` should be reinterpreted under the corrected definition.

## v22 Temporal Cost Gate Recompute (precrash precision)

- Script: `scripts/report_logos_shadow_cost_gate_temporal_v22.py`
- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_cost_gate_temporal_v22_latest.json`
- Definition: `avg_precrash_zone_precision` over `t1/t2/t3` (same splits as v15), cost formula aligned with inline sweeps (`load_coeff=4.8`, `false_coeff=1.5`).
- Snapshot (v20 precision-layer preset):
  - `cost_efficiency_score=0.264388`
  - `pass_cost_gate=false`
- `report_logos_shadow_cost_gate_v5.py` note updated to point evaluators at v22 for post-v21 precision semantics.

### v22 Guard

- Temporal gate remains blocked under corrected precision; this is expected until model quality improves.
- Keep `OBSERVATION_ONLY`.

## v23 Evaluation Bundle + shared eval lib

- Library: `scripts/logos_shadow_eval_lib.py` (yfinance slice, window subprocess, `aggregate_cost_metrics`).
- Bundle script: `scripts/report_logos_shadow_evaluation_bundle_v23.py`
- Report: `reports/research/logos_shadow_v1/logos_kospi_shadow_evaluation_bundle_v23_latest.json`
- Refactor: `scripts/report_logos_shadow_cost_gate_temporal_v22.py` delegates to the same lib (no duplicated subprocess wiring).
- Windows: temporal `t1`–`t3` (same splits as v15); holdout `h1`–`h4` (euro deval, CN deval, 2018 risk-off, 2022 rate shock).
- Snapshot A — `--bare` (추가 인자 없음; 베이스라인 비교용, `min_cost_efficiency_score=0.35`):
  - temporal: `cost_efficiency_score=0.068596`, `pass_cost_gate=false`
  - holdout: `cost_efficiency_score=0.095507`, `pass_cost_gate=false`
  - combined (7 windows): `combined_cost_efficiency_score=0.084797`, `combined_pass=false`
- Snapshot B — `DEFAULT_SHADOW_EXTRA` (`logos_kospi_shadow_evaluation_bundle_v23_latest.json` SSOT, 2026-04-03 재생성 기준):
  - temporal: `cost_efficiency_score≈0.127156`, `pass_cost_gate=false`
  - holdout: `cost_efficiency_score≈0.590553`, `pass_cost_gate=true`
  - combined: `cost_efficiency_score≈0.393851`, `pass_cost_gate=true`
- Regression tests: `tests/test_logos_kospi_shadow_metrics_v21.py` (asserts `warning_precision == precrash_zone_precision`, schema `logos_kospi_shadow_v1_1`).

### v23 Guard

- Bundle is research orchestration only; compare **같은 `extra_args`·같은 창**에서 v22 temporal과의 차이를 말할 것. 스택 A(bare) vs B(default-extra)는 게이트 결과가 다를 수 있음.
- Keep `OBSERVATION_ONLY`.

## Interpretation (Fact-Locked)

- Current logos lens output is a root 4D numeric stub and produces a neutral directional sign in this run.
- Recall is high in the synthetic shadow sample (`1.0`), but directional hit is not meaningful with neutral direction output.
- This result is valid for research tracking and does not imply market-ready directional forecasting.

## Governance

- Keep this track in `OBSERVATION_ONLY`.
- Do not bind this result to live triggers, sizing, or A-track promotion without separate gate approval.
- After commander L1 `GO` commit, re-run:
  - `py scripts/verify_l1_go_impact.py`
  - `py scripts/run_logos_kospi_shadow_test.py`
  and compare deltas before any policy change.

