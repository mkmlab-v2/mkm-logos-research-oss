# Daily execution insight — 1-page brief (generated)

**AUTO:** `scripts/build_daily_execution_insight_brief_v1.py` — Fact-Lock sources only; not LLM prose.

## 0) Meta

| `brief_date_utc` | 2026-05-09 |
| `workspace_anchor` | BTC spot / operator anchor — set via CLI if needed |
| `mode` | `OBSERVATION_ONLY` |

## 1) Execution facts (disk)

### 1a) Dual regime (snippet only — no full `interpretation` in brief)

- **Thin row:** `C:/workspace/docs/final/artifacts/multilens_eval_v2_thin_report_latest.json` row `calendar_date=2023-03-10`

**`interpretation_snippet`:**

```
dual_regime: gate_profile=balanced; PSI=0.60 (warn>0.60, crisis>0.80); bible_risk=0.33; stress=0.44; cap=0.89; state_clamp=on;state_id=2;state_cap_noop=1.0000
```

**Snapshot (one line):** `risk_multiplier_cap` = 0.8899 · `market_shock_confirmed` = False · `veto_triggered` = False

### 1b) Independent lens fusion stub (`conflict_summary`)

- **Source:** `C:/workspace/docs/final/artifacts/independent_lens_fusion_stub_latest.json`

- **`minority_lens_ids`:** `["logos"]`
- **`logos_evidence_verse_ids`:** `["sample-001", "sample-002", "sample-003"]`

**`conflict_narrative_guarded`:**

```
Lens direction alignment: majority_sign=bull, agreement_rate=0.75, conflict_count=1. Minority vs majority: logos differ from majority_sign=bull. Breakdown: myeongni: sign=bull, score=0.080000, conf=0.685520; sasang: sign=bull, score=0.170000, conf=0.711500; logos: sign=bear, score=-0.323333, conf=0.200000; market_sasang: sign=bull, score=0.170000, conf=0.081912. Logos evidence verse_id anchors (batch-bound): sample-001, sample-002, sample-003. Logos hash-tagged snippet (clipped): [#sample-001] [#sample-002] [#sample-003]
```

### 1c) Independent lens snapshots (latest JSON — numeric / structured facts only)

#### Myeongni (`myeongni_independent_lens_latest`)

| field | value |
|-------|-------|
| `ts_utc` | 2026-05-06T00:33:42Z |
| `schema` | myeongni_independent_lens_v0 |
| `direction_score` | 0.08 |
| `confidence` | 0.6855 |
| `state_id` | 15 |
| `run_id` | calendar_stub_through_202604 |

#### Market Myeongni (`market_myeongni_lens_latest`)

| field | value |
|-------|-------|
| `ts_utc` | 2026-05-09T01:06:15Z |
| `direction_score` (overlay) | 0.0536 |
| `confidence` (overlay) | 0.6033 |
| `direction_sign` | neutral |
| `base_direction_score` | 0.08 |
| `base_confidence` | 0.6855 |
| `direction_score_scale` | 0.92 |
| `confidence_scale` | 0.88 |
| `policy_path` | `C:\workspace\data\market_myeongni\market_myeongni_overlay_policy_v1.json` |

#### Myeongni conflict arbitration runtime (B-track policy stamp)

> Policy mode / verification only — not a price signal and not wired to live execution.

| field | value |
|-------|-------|
| `mode` | aggressive |
| `verification_pass` | True |
| `policy_hash` | `14edd9bd1e2b…` |
| `generated_at_utc` | 2026-05-09T00:44:22Z |
| `policy_path` | `C:\workspace\data\myeongni\myeongni_conflict_arbitration_v1.json` |

#### Sasang (`sasang_independent_lens_latest`)

| field | value |
|-------|-------|
| `ts_utc` | 2026-05-09T01:55:32Z |
| `mapping_target` | sideways |
| `regime_hypothesis` | phase_transition |
| `direction_score` | 0.17 |
| `confidence` | 0.7115 |
| `heat_proxy` | 0.585 |
| `cold_proxy` | 0.415 |
| `volatility_rarefaction_proxy` | 0.48 |

##### `b_track_axis_scores_v1` (동역학 프록시만; 보명·금화 본론 정량 아님)

| field | value |
|-------|-------|
| `heat_proxy` | 0.585 |
| `cold_proxy` | 0.415 |
| `volatility_rarefaction_proxy` | 0.48 |
| `thermal_imbalance_proxy` | 0.17 |

> 동역학 JSONL machine_readables 파생 프록시만; 보명지조·금화교역 본론 정량 아님.

#### Market Sasang (`market_sasang_lens_latest`)

| field | value |
|-------|-------|
| `ts_utc` | 2026-05-05T08:27:56Z |

- **human_commander banner:** [TRACK B / HYPO] 연구용·비자동 — 최종 채택은 지휘관 판단 대기
- **`veto.force_hold`:** `True` · `reason_codes` = `["HIGH_ENTROPY_SOFTMAX"]`
- **`composite_uncertainty`:** 0.6724 · `entropy_norm_4way` = 0.9864

| softmax key | p |
|-------------|---|
| `taeyang` | 0.3145 |
| `soyang` | 0.2788 |
| `taeeum` | 0.1961 |
| `soeum` | 0.2106 |

#### Logos independent lens (`logos_independent_lens_latest`)

| field | value |
|-------|-------|
| `ts_utc` | 2026-05-05T08:27:57Z |
| `direction_score` | -0.3233 |
| `confidence` | 0.2 |
| `evidence_refs_count` | 3 |

**`narrative_snippet_guarded` (hash-tagged only):**

```
[#sample-001] [#sample-002] [#sample-003]
```

### 1d) Fact-Lock governance snapshot (A-track / backtest / commander overlay)

| field | value | source |
|-------|-------|--------|
| `overall_go_no_go` | `GO` | `C:/workspace/docs/final/artifacts/a_track_go_nogo_status_latest.json` |
| `recommended_stage` | `S4_LIMITED_LIVE` | `C:/workspace/docs/final/artifacts/a_track_go_nogo_status_latest.json` |
| `failed_reasons` | `[]` | `C:/workspace/docs/final/artifacts/a_track_go_nogo_status_latest.json` |
| `high_reliability_decision` | `PASS` | `C:/workspace/docs/final/artifacts/a_track_go_nogo_status_latest.json` |
| `price_output_locked` | `False` | `C:/workspace/docs/final/artifacts/a_track_go_nogo_status_latest.json` |
| `price_output_unlocked(check)` | `True` | `C:/workspace/docs/final/artifacts/a_track_go_nogo_status_latest.json` |
| `prophecy.meta.high_reliability_decision` | `PASS` | `C:/workspace/docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.json` |
| `prophecy.meta.price_output_locked` | `False` | `C:/workspace/docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.json` |
| `best_strategy.strategy_id` | `myeongni+sasang` | `C:/workspace/docs/final/artifacts/prophecy_lens_combo_backtest_v1_latest.json` |
| `best_strategy.metrics.n_days` | `29` | `C:/workspace/docs/final/artifacts/prophecy_lens_combo_backtest_v1_latest.json` |
| `best_strategy.metrics.mdd` | `-0.0363` | `C:/workspace/docs/final/artifacts/prophecy_lens_combo_backtest_v1_latest.json` |
| `best_strategy.metrics.sharpe` | `5.838` | `C:/workspace/docs/final/artifacts/prophecy_lens_combo_backtest_v1_latest.json` |
| `16state.states_with_audit` | `11` | `C:/workspace/data/myeongni/16_STATE_MASTER_PROBE_v1.json` |
| `16state.states_total` | `16` | `C:/workspace/data/myeongni/16_STATE_MASTER_PROBE_v1.json` |
| `commander.scores.confidence` | `0.6767` | `C:/workspace/reports/commander_myeongni_lens_latest.json` |
| `commander.scores.direction_score` | `0.1051` | `C:/workspace/reports/commander_myeongni_lens_latest.json` |
| `sasang.hard_guardrails.most_conservative_wins` | `True` | `C:/workspace/docs/final/artifacts/sasang_veto_only_active_config_latest.json` |
| `sasang.hard_guardrails.directional_entry_disabled` | `True` | `C:/workspace/docs/final/artifacts/sasang_veto_only_active_config_latest.json` |

- **Label discipline:** `GO`/`HOLD`는 운영 게이트(`overall_go_no_go`) 기준, `PASS`/`FAIL`은 개별 체크(`high_reliability_decision` 등) 기준으로 분리 기록.

### 1e) Myeongri core v2 upgrade (jijangan vector / research shinsal / size reco)

| field | value | source |
|-------|-------|--------|
| `output.size_multiplier_recommended` | `0.5217` | `C:/workspace/reports/myeongri_core_v2_upgrade_latest.json` |
| `output.commander_overlay_multiplier` | `0.5217` | `C:/workspace/reports/myeongri_core_v2_upgrade_latest.json` |
| `output.direction_override_allowed` | `False` | `C:/workspace/reports/myeongri_core_v2_upgrade_latest.json` |
| `neutral.structural_tension_v1` | `0.3` | `C:/workspace/reports/myeongri_core_v2_upgrade_latest.json` |
| `neutral.latent_energy_vector_4d` | `[0.238636, 0.068182, 0.363636, 0.329545]` | `C:/workspace/reports/myeongri_core_v2_upgrade_latest.json` |
| `shinsal_detection_logs.entries` | `2` | `C:/workspace/reports/myeongri_core_v2_upgrade_latest.json` |

> [MKM-B-TRACK-NOTICE] These Myeongri metrics are [HYPOTHESIS] overlays derived from traditional structure heuristics; they are not market price, fill, or liquidity facts. They must not drive live kill-switches or direction; use only as operator-side observation and optional size-only advisory where explicitly gated.

| `jijangan.elements.wood` | `0.2386` | `C:/workspace/reports/myeongri_core_v2_upgrade_latest.json` |
| `jijangan.elements.fire` | `0.06818` | `C:/workspace/reports/myeongri_core_v2_upgrade_latest.json` |
| `jijangan.elements.earth` | `0.3636` | `C:/workspace/reports/myeongri_core_v2_upgrade_latest.json` |
| `jijangan.elements.metal` | `0.02273` | `C:/workspace/reports/myeongri_core_v2_upgrade_latest.json` |
| `jijangan.elements.water` | `0.3068` | `C:/workspace/reports/myeongri_core_v2_upgrade_latest.json` |
| `shinsal.detected_count` | `2` | `C:/workspace/reports/myeongri_core_v2_upgrade_latest.json` |
| `shinsal.detected_ids` | `gwaegang_like, baekho_like` | `C:/workspace/reports/myeongri_core_v2_upgrade_latest.json` |

- **Labels:** `[RESEARCH_ONLY]` on `shinsal_impact_overlay`; `neutral_structure_metrics_v1` is [HYPOTHESIS] geometry only (not price/vol); size output is advisory overlay only (no A-track direction).

## 2) Hypothesis / insight ([HYPO] — not A-track trigger)

| item | memo |
|------|------|
| hypothesis one-liner | *(operator)* |
| next check script / artifact | *(operator)* |

## 3) Final action (gate vocabulary only)

| field | value |
|-------|-------|
| `final_action_label` | *(operator)* |
| `evidence_paths` | `C:/workspace/docs/final/artifacts/multilens_eval_v2_thin_report_latest.json`; `C:/workspace/docs/final/artifacts/independent_lens_fusion_stub_latest.json`; `C:/workspace/docs/final/artifacts/myeongni_independent_lens_latest.json`; `C:/workspace/docs/final/artifacts/market_myeongni_lens_latest.json`; `C:/workspace/reports/myeongni_conflict_arbitration_runtime_mode_latest.json`; `C:/workspace/docs/final/artifacts/sasang_independent_lens_latest.json`; `C:/workspace/docs/final/artifacts/market_sasang_lens_latest.json`; `C:/workspace/docs/final/artifacts/logos_independent_lens_latest.json`; `C:/workspace/docs/final/artifacts/a_track_go_nogo_status_latest.json`; `C:/workspace/reports/myeongri_core_v2_upgrade_latest.json` |

---

_Generator flags:_ `thin_ok=True` `calendar_pick=2023-03-10` `fusion_ok=True` `independent_lens_ok={"myeongni": true, "market_myeongni": true, "myeongni_conflict_runtime": true, "sasang": true, "market_sasang": true, "logos_independent": true, "governance_factlock": true, "myeongri_v2_upgrade": true}`
