# LOGOS Shadow Weekly Gate Operation Rule v1

## Scope
- This rule applies to `S1_SHADOW` observation only.
- This rule does not enable auto-trading or A-track auto-promotion.
- Response mode and quality policy reference:
  - `docs/final/artifacts/LOGOS_RESPONSE_POLICY_INTERNAL_EXTERNAL_V1.md`

## Inputs and Outputs
- Daily source log: `reports/logos_shadow_daily_metrics_log_v1.jsonl`
- Strict gate output: `docs/final/artifacts/logos_shadow_weekly_gate_latest.json`
- Bootstrap gate output: `docs/final/artifacts/logos_shadow_weekly_gate_bootstrap_latest.json`
- Alert output: `docs/final/artifacts/logos_shadow_alert_decision_latest.json`

## Weekly Gate Profiles
- `strict` profile:
  - `min_samples=3`
  - `provisional_gate=false`
- `bootstrap` profile:
  - `min_samples=1`
  - `provisional_gate=true` (provisional gate for early observation)

## Gate Thresholds (7-day window defaults)
- `min_mean_top1_cosine = 0.08`
- `max_low_confidence_rate = 0.60`
- `max_query_error_rate = 0.20`

## Decision Logic
- Gate checks:
  - `min_samples_pass`
  - `mean_top1_cosine_pass`
  - `low_conf_rate_pass`
  - `query_error_rate_pass`
- Gate decision:
  - `GO`: all checks pass
  - `WATCH`: sample check passes but one or more quality checks fail
  - `HOLD`: sample check fails

## Alert Logic
- Alert script: `scripts/build_logos_shadow_alert_decision_v1.py`
- `should_alert=true` if either:
  - `strict == HOLD`, or
  - `strict != bootstrap` (decision mismatch)
- `should_alert=false` if:
  - strict and bootstrap are aligned and strict is not HOLD

## Webhook Send Rule
- Sending only occurs when all conditions are true:
  - `--send-webhook` requested
  - `should_alert=true`
  - webhook URL is configured
- URL resolution priority:
  - `LOGOS_SHADOW_ALERT_WEBHOOK_URL`
  - `OPS_ALARM_WEBHOOK_URL`
- If `should_alert=false`, webhook status is `suppressed_by_rule`.

## Weekly Promotion Review Template Input
- Review template input pack (single source set):
  - `docs/final/artifacts/logos_shadow_weekly_gate_latest.json` (strict decision)
  - `docs/final/artifacts/logos_shadow_weekly_gate_bootstrap_latest.json` (bootstrap decision)
  - `docs/final/artifacts/logos_shadow_weekly_trend_report_latest.json` (7-day trend)
  - `docs/final/artifacts/logos_shadow_alert_decision_latest.json` (alert decision)
  - `docs/final/artifacts/logos_shadow_insight_latest.json` (shadow insight + deep fusion evidence)
- Minimum review lines to copy into weekly approval notes:
  - `strict.decision`, `strict.metrics.samples`
  - `bootstrap.decision`, `bootstrap.metrics.samples`
  - `trend.summary.mean_top1_cosine_7d_avg`
  - `trend.summary.low_conf_rate_7d_avg`
  - `trend.summary.query_error_rate_7d_aggregate`
  - `alert.should_alert`, `alert.reason`

## Track Wall (Fact-Lock)
- `shadow_only=true`
- `auto_trade_enable=false`
- `promotion_to_a_track_allowed=false`
- Human review remains required per release gate.

## Promotion KPI Contract (S1_SHADOW -> next stage)
- Purpose:
  - Keep exploration freedom high in B/SHADOW while making promotion evidence deterministic.
- Mandatory promotion gate (all required):
  - `strict.decision == GO` for at least 2 consecutive weekly windows
  - `strict.metrics.samples >= 7` in each promotion-reviewed window
  - `trend.summary.mean_top1_cosine_7d_avg >= 0.10`
  - `trend.summary.query_error_rate_7d_aggregate <= 0.05`
  - `trend.summary.low_conf_rate_7d_avg <= 0.30`
  - `alert.should_alert == false` in the latest weekly review snapshot
  - Regression bundle pass (including:
    - `tests/test_promote_logos_to_shadow_live_v1.py`
    - `tests/test_build_logos_shadow_alert_decision_v1.py`)
- Interpretation rule:
  - If any KPI fails, keep stage at `S1_SHADOW` and continue optimization in B/SHADOW.
  - No auto-bridge to A-track/live; promotion remains human-approved.

## Daily Optimization Loop (Performance-first, Wall-safe)
- Daily:
  - Run MacroDailyFusion chain and refresh:
    - weekly gates
    - weekly trend
    - alert decision
    - shadow insight
    - ops dashboard
- Weekly:
  - Review KPI contract lines from:
    - strict/ bootstrap gate outputs
    - trend report
    - alert decision
    - shadow insight
- Action:
  - If KPI improving but not yet qualified: continue query/model/corpus optimization in SHADOW.
  - If KPI contract satisfied: prepare promotion package for human approval.

