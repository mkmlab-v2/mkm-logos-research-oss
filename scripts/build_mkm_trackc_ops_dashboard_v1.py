from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _status_or_default(value: Any, default: str = "UNKNOWN") -> Any:
    if value is None:
        return default
    if isinstance(value, str) and not value.strip():
        return default
    return value


def _parse_iso_utc(value: Any) -> datetime | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _forward_pipeline_health(
    *,
    prereg: Dict[str, Any],
    latest: Dict[str, Any],
    weekly: Dict[str, Any],
    now: datetime,
) -> Dict[str, Any]:
    prereg_hash = str(prereg.get("preregister_hash_sha256") or "")
    latest_row = latest.get("latest_row") or {}
    latest_hash = str(latest_row.get("preregister_hash_sha256") or "")
    hash_match = bool(prereg_hash and latest_hash and prereg_hash == latest_hash)

    rows_total = int(latest.get("rows_total") or 0)
    rows_in_window = int(weekly.get("rows_in_window") or 0)
    state_counts = weekly.get("decision_state_counts") or {}
    total_counted = sum(int(v or 0) for v in state_counts.values()) if isinstance(state_counts, dict) else 0

    latest_ts = _parse_iso_utc(latest.get("generated_at_utc"))
    is_fresh_72h = bool(latest_ts and (now - latest_ts).total_seconds() <= 72 * 3600)

    passed = bool(hash_match and rows_total > 0 and rows_in_window > 0 and total_counted > 0 and is_fresh_72h)
    reasons: list[str] = []
    if not hash_match:
        reasons.append("preregister_hash_mismatch")
    if rows_total <= 0:
        reasons.append("no_forward_rows")
    if rows_in_window <= 0:
        reasons.append("no_rows_in_window")
    if total_counted <= 0:
        reasons.append("no_decision_counts")
    if not is_fresh_72h:
        reasons.append("stale_latest_snapshot")

    return {
        "status": "PASS" if passed else "FAIL",
        "passed": passed,
        "reason_codes": reasons,
        "preregister_hash_match": hash_match,
        "rows_total": rows_total,
        "rows_in_window_7d": rows_in_window,
        "latest_snapshot_fresh_within_72h": is_fresh_72h,
        "latest_generated_at_utc": latest.get("generated_at_utc"),
    }


def main() -> int:
    root = Path("C:/workspace")
    art = root / "docs" / "final" / "artifacts"
    now = datetime.now(timezone.utc)

    status = _read_json(art / "mkm_ai_status_pointer_latest.json")
    decision = _read_json(art / "mkm_ai_v2_promotion_decision_latest.json")
    handoff = _read_json(art / "mkm_trackc_client_handoff_package_latest.json")
    acceptance = _read_json(art / "mkm_trackc_operational_acceptance_latest.json")
    freeze = _read_json(art / "mkm_trackc_delivery_freeze_log_latest.json")
    guard = _read_json(art / "mkm_trackc_client_handoff_guard_latest.json")
    drill = _read_json(art / "mkm_trackc_guard_recovery_drill_latest.json")
    paddle = _read_json(art / "paddle_onboarding_status_latest.json")
    dual_leg_brief = _read_json(art / "trackc_prophecy_dual_leg_brief_latest.json")
    logos_shadow = _read_json(art / "logos_shadow_promotion_status_latest.json")
    logos_insight = _read_json(art / "logos_shadow_insight_latest.json")
    logos_drift = _read_json(art / "logos_semantic_drift_monitor_latest.json")
    logos_regime_resonance_shadow = _read_json(art / "logos_regime_resonance_shadow_signal_latest.json")
    logos_weekly_gate = _read_json(art / "logos_shadow_weekly_gate_latest.json")
    logos_weekly_gate_bootstrap = _read_json(art / "logos_shadow_weekly_gate_bootstrap_latest.json")
    logos_weekly_trend = _read_json(art / "logos_shadow_weekly_trend_report_latest.json")
    logos_kpi_progress = _read_json(art / "logos_shadow_promotion_kpi_progress_latest.json")
    logos_response_policy_check = _read_json(art / "logos_response_policy_check_latest.json")
    logos_review_packet = _read_json(art / "logos_s1_shadow_promotion_review_packet_latest.json")
    forward_prereg = _read_json(art / "macro_risk_forward_preregister_lock_latest.json")
    forward_latest = _read_json(art / "macro_risk_forward_log_latest.json")
    forward_weekly = _read_json(art / "macro_risk_forward_weekly_report_latest.json")
    forward_health = _forward_pipeline_health(
        prereg=forward_prereg,
        latest=forward_latest,
        weekly=forward_weekly,
        now=now,
    )

    dashboard = {
        "schema": "mkm_trackc_ops_dashboard_v1",
        "generated_at_utc": _utc_now(),
        "system": {
            "label": status.get("system_label"),
            "status": status.get("status"),
            "is_final": status.get("is_final"),
            "promotion_decision": decision.get("decision"),
            "promotion_ready": decision.get("promotion_ready"),
            "weekly_pass_rate_percent": status.get("weekly_pass_rate_percent"),
            "weekly_sample_count": status.get("weekly_sample_count"),
        },
        "trackc": {
            "packet_status": _status_or_default(handoff.get("packet_status"), "UNKNOWN"),
            "api_decision_state": _status_or_default(
                (handoff.get("executive_summary") or {}).get("api_decision_state"),
                "UNKNOWN",
            ),
            "showroom_go_no_go": _status_or_default(
                (handoff.get("executive_summary") or {}).get("showroom_go_no_go"),
                "UNKNOWN",
            ),
            "guard_passed": guard.get("passed"),
            "acceptance_status": _status_or_default(acceptance.get("status"), "NOT_RUN"),
            "freeze_status": _status_or_default(freeze.get("status"), "NOT_RUN"),
            "recovery_drill_status": _status_or_default(drill.get("status"), "NOT_RUN"),
            "paddle_runbook_present": (art / "PADDLE_ONBOARDING_SECURE_RUNBOOK_V1.md").exists(),
            "paddle_onboarding_status": paddle.get("status", "RUNBOOK_READY"),
            "dual_leg_recent_trading_days": (dual_leg_brief.get("window") or {}).get("recent_trading_days"),
            "dual_leg_kospi_hit_rate": ((dual_leg_brief.get("legs") or {}).get("kospi") or {}).get("price_directional_hit_rate"),
            "dual_leg_btc_hit_rate": ((dual_leg_brief.get("legs") or {}).get("btc") or {}).get("price_directional_hit_rate"),
            "dual_leg_btc_minus_kospi_hit_rate": (dual_leg_brief.get("delta") or {}).get("btc_minus_kospi_hit_rate"),
            "forward_pipeline_health": forward_health,
            "logos_shadow": {
                "grade": ((logos_shadow.get("promotion") or {}).get("to")),
                "approved": ((logos_shadow.get("promotion") or {}).get("approved")),
                "decision": ((logos_insight.get("summary") or {}).get("decision")),
                "top_match_verse_id": ((logos_insight.get("summary") or {}).get("top_match_verse_id")),
                "top_match_cosine": ((logos_insight.get("summary") or {}).get("top_match_cosine")),
                "mean_top1_cosine": ((logos_insight.get("summary") or {}).get("mean_top1_cosine")),
                "queries_ok": ((logos_insight.get("summary") or {}).get("queries_ok")),
                "queries_error": ((logos_insight.get("summary") or {}).get("queries_error")),
                "low_confidence": ((logos_drift.get("guard") or {}).get("low_confidence")),
                "resonance_shadow_status": logos_regime_resonance_shadow.get("status"),
                "resonance_shadow_scanned_regimes": ((logos_regime_resonance_shadow.get("summary") or {}).get("scanned_regimes")),
                "resonance_shadow_best_regime": ((logos_regime_resonance_shadow.get("summary") or {}).get("best_regime")),
                "resonance_shadow_best_top_hit_cosine": ((logos_regime_resonance_shadow.get("summary") or {}).get("best_top_hit_cosine")),
                "weekly_gate_decision_strict": logos_weekly_gate.get("decision"),
                "weekly_gate_decision_bootstrap": logos_weekly_gate_bootstrap.get("decision"),
                "weekly_gate_samples_strict": ((logos_weekly_gate.get("metrics") or {}).get("samples")),
                "weekly_gate_samples_bootstrap": ((logos_weekly_gate_bootstrap.get("metrics") or {}).get("samples")),
                "weekly_trend_samples": logos_weekly_trend.get("samples"),
                "weekly_trend_mean_top1_cosine_7d_avg": ((logos_weekly_trend.get("summary") or {}).get("mean_top1_cosine_7d_avg")),
                "weekly_trend_low_conf_rate_7d_avg": ((logos_weekly_trend.get("summary") or {}).get("low_conf_rate_7d_avg")),
                "weekly_trend_query_error_rate_7d_avg": ((logos_weekly_trend.get("summary") or {}).get("query_error_rate_7d_avg")),
                "kpi_progress_status": logos_kpi_progress.get("status"),
                "kpi_progress_passed": logos_kpi_progress.get("passed"),
                "kpi_progress_consecutive_go": logos_kpi_progress.get("consecutive_strict_go_windows"),
                "kpi_progress_required_consecutive_go": logos_kpi_progress.get("required_consecutive_strict_go_windows"),
                "response_policy_check_status": logos_response_policy_check.get("status"),
                "response_policy_check_passed": logos_response_policy_check.get("passed"),
                "promotion_review_packet_generated_at": logos_review_packet.get("generated_at_utc"),
                "promotion_review_packet_kpi_status": (
                    ((logos_review_packet.get("summary") or {}).get("kpi_contract") or {}).get("status")
                ),
            },
        },
        "evidence": {
            "status_pointer": "docs/final/artifacts/mkm_ai_status_pointer_latest.json",
            "promotion_decision": "docs/final/artifacts/mkm_ai_v2_promotion_decision_latest.json",
            "handoff_package": "docs/final/artifacts/mkm_trackc_client_handoff_package_latest.json",
            "handoff_guard": "docs/final/artifacts/mkm_trackc_client_handoff_guard_latest.json",
            "acceptance": "docs/final/artifacts/mkm_trackc_operational_acceptance_latest.json",
            "freeze_log": "docs/final/artifacts/mkm_trackc_delivery_freeze_log_latest.json",
            "recovery_drill": "docs/final/artifacts/mkm_trackc_guard_recovery_drill_latest.json",
            "paddle_onboarding_runbook": "docs/final/artifacts/PADDLE_ONBOARDING_SECURE_RUNBOOK_V1.md",
            "paddle_onboarding_status": "docs/final/artifacts/paddle_onboarding_status_latest.json",
            "dual_leg_brief_json": "docs/final/artifacts/trackc_prophecy_dual_leg_brief_latest.json",
            "dual_leg_brief_md": "docs/final/artifacts/trackc_prophecy_dual_leg_brief_latest.md",
            "logos_shadow_promotion_status": "docs/final/artifacts/logos_shadow_promotion_status_latest.json",
            "logos_shadow_insight": "docs/final/artifacts/logos_shadow_insight_latest.json",
            "logos_semantic_drift_monitor": "docs/final/artifacts/logos_semantic_drift_monitor_latest.json",
            "logos_regime_resonance_shadow": "docs/final/artifacts/logos_regime_resonance_shadow_signal_latest.json",
            "logos_shadow_weekly_gate": "docs/final/artifacts/logos_shadow_weekly_gate_latest.json",
            "logos_shadow_weekly_gate_bootstrap": "docs/final/artifacts/logos_shadow_weekly_gate_bootstrap_latest.json",
            "logos_shadow_weekly_trend": "docs/final/artifacts/logos_shadow_weekly_trend_report_latest.json",
            "logos_shadow_kpi_progress": "docs/final/artifacts/logos_shadow_promotion_kpi_progress_latest.json",
            "logos_response_policy_check": "docs/final/artifacts/logos_response_policy_check_latest.json",
            "logos_s1_shadow_promotion_review_packet": "docs/final/artifacts/logos_s1_shadow_promotion_review_packet_latest.json",
            "forward_preregister_lock": "docs/final/artifacts/macro_risk_forward_preregister_lock_latest.json",
            "forward_log_latest": "docs/final/artifacts/macro_risk_forward_log_latest.json",
            "forward_weekly_report": "docs/final/artifacts/macro_risk_forward_weekly_report_latest.json",
        },
    }

    out_json = art / "mkm_trackc_ops_dashboard_latest.json"
    out_md = art / "mkm_trackc_ops_dashboard_latest.md"
    out_json.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# MKM Track C Ops Dashboard",
        "",
        f"- generated_at_utc: `{dashboard['generated_at_utc']}`",
        f"- system_status: `{dashboard['system']['status']}`",
        f"- promotion_decision: `{dashboard['system']['promotion_decision']}`",
        f"- promotion_ready: `{dashboard['system']['promotion_ready']}`",
        f"- weekly_pass_rate_percent: `{dashboard['system']['weekly_pass_rate_percent']}`",
        f"- weekly_sample_count: `{dashboard['system']['weekly_sample_count']}`",
        "",
        "## Track C",
        f"- packet_status: `{dashboard['trackc']['packet_status']}`",
        f"- api_decision_state: `{dashboard['trackc']['api_decision_state']}`",
        f"- showroom_go_no_go: `{dashboard['trackc']['showroom_go_no_go']}`",
        f"- guard_passed: `{dashboard['trackc']['guard_passed']}`",
        f"- acceptance_status: `{dashboard['trackc']['acceptance_status']}`",
        f"- freeze_status: `{dashboard['trackc']['freeze_status']}`",
        f"- recovery_drill_status: `{dashboard['trackc']['recovery_drill_status']}`",
        f"- paddle_runbook_present: `{dashboard['trackc']['paddle_runbook_present']}`",
        f"- paddle_onboarding_status: `{dashboard['trackc']['paddle_onboarding_status']}`",
        f"- dual_leg_recent_trading_days: `{dashboard['trackc']['dual_leg_recent_trading_days']}`",
        f"- dual_leg_kospi_hit_rate: `{dashboard['trackc']['dual_leg_kospi_hit_rate']}`",
        f"- dual_leg_btc_hit_rate: `{dashboard['trackc']['dual_leg_btc_hit_rate']}`",
        f"- dual_leg_btc_minus_kospi_hit_rate: `{dashboard['trackc']['dual_leg_btc_minus_kospi_hit_rate']}`",
        f"- forward_pipeline_health: `{(dashboard['trackc']['forward_pipeline_health'] or {}).get('status')}`",
        f"- forward_pipeline_reason_codes: `{(dashboard['trackc']['forward_pipeline_health'] or {}).get('reason_codes')}`",
        f"- forward_pipeline_rows_total: `{(dashboard['trackc']['forward_pipeline_health'] or {}).get('rows_total')}`",
        f"- forward_pipeline_rows_in_window_7d: `{(dashboard['trackc']['forward_pipeline_health'] or {}).get('rows_in_window_7d')}`",
        "",
        "## [SHADOW_INSIGHT]",
        f"- shadow_grade: `{((dashboard['trackc']['logos_shadow'] or {}).get('grade'))}`",
        f"- shadow_approved: `{((dashboard['trackc']['logos_shadow'] or {}).get('approved'))}`",
        f"- decision: `{((dashboard['trackc']['logos_shadow'] or {}).get('decision'))}`",
        f"- top_match_verse_id: `{((dashboard['trackc']['logos_shadow'] or {}).get('top_match_verse_id'))}`",
        f"- top_match_cosine: `{((dashboard['trackc']['logos_shadow'] or {}).get('top_match_cosine'))}`",
        f"- mean_top1_cosine: `{((dashboard['trackc']['logos_shadow'] or {}).get('mean_top1_cosine'))}`",
        f"- queries_ok: `{((dashboard['trackc']['logos_shadow'] or {}).get('queries_ok'))}`",
        f"- queries_error: `{((dashboard['trackc']['logos_shadow'] or {}).get('queries_error'))}`",
        f"- low_confidence: `{((dashboard['trackc']['logos_shadow'] or {}).get('low_confidence'))}`",
        f"- resonance_shadow_status: `{((dashboard['trackc']['logos_shadow'] or {}).get('resonance_shadow_status'))}`",
        f"- resonance_shadow_scanned_regimes: `{((dashboard['trackc']['logos_shadow'] or {}).get('resonance_shadow_scanned_regimes'))}`",
        f"- resonance_shadow_best_regime: `{((dashboard['trackc']['logos_shadow'] or {}).get('resonance_shadow_best_regime'))}`",
        f"- resonance_shadow_best_top_hit_cosine: `{((dashboard['trackc']['logos_shadow'] or {}).get('resonance_shadow_best_top_hit_cosine'))}`",
        f"- weekly_gate_decision_strict: `{((dashboard['trackc']['logos_shadow'] or {}).get('weekly_gate_decision_strict'))}`",
        f"- weekly_gate_samples_strict: `{((dashboard['trackc']['logos_shadow'] or {}).get('weekly_gate_samples_strict'))}`",
        f"- weekly_gate_decision_bootstrap: `{((dashboard['trackc']['logos_shadow'] or {}).get('weekly_gate_decision_bootstrap'))}`",
        f"- weekly_gate_samples_bootstrap: `{((dashboard['trackc']['logos_shadow'] or {}).get('weekly_gate_samples_bootstrap'))}`",
        f"- weekly_trend_samples: `{((dashboard['trackc']['logos_shadow'] or {}).get('weekly_trend_samples'))}`",
        f"- weekly_trend_mean_top1_cosine_7d_avg: `{((dashboard['trackc']['logos_shadow'] or {}).get('weekly_trend_mean_top1_cosine_7d_avg'))}`",
        f"- weekly_trend_low_conf_rate_7d_avg: `{((dashboard['trackc']['logos_shadow'] or {}).get('weekly_trend_low_conf_rate_7d_avg'))}`",
        f"- weekly_trend_query_error_rate_7d_avg: `{((dashboard['trackc']['logos_shadow'] or {}).get('weekly_trend_query_error_rate_7d_avg'))}`",
        f"- kpi_progress_status: `{((dashboard['trackc']['logos_shadow'] or {}).get('kpi_progress_status'))}`",
        f"- kpi_progress_passed: `{((dashboard['trackc']['logos_shadow'] or {}).get('kpi_progress_passed'))}`",
        f"- kpi_progress_consecutive_go: `{((dashboard['trackc']['logos_shadow'] or {}).get('kpi_progress_consecutive_go'))}`",
        f"- kpi_progress_required_consecutive_go: `{((dashboard['trackc']['logos_shadow'] or {}).get('kpi_progress_required_consecutive_go'))}`",
        f"- response_policy_check_status: `{((dashboard['trackc']['logos_shadow'] or {}).get('response_policy_check_status'))}`",
        f"- response_policy_check_passed: `{((dashboard['trackc']['logos_shadow'] or {}).get('response_policy_check_passed'))}`",
        f"- promotion_review_packet_generated_at: `{((dashboard['trackc']['logos_shadow'] or {}).get('promotion_review_packet_generated_at'))}`",
        f"- promotion_review_packet_kpi_status: `{((dashboard['trackc']['logos_shadow'] or {}).get('promotion_review_packet_kpi_status'))}`",
        "",
        "## Evidence",
        "- `docs/final/artifacts/mkm_ai_status_pointer_latest.json`",
        "- `docs/final/artifacts/mkm_ai_v2_promotion_decision_latest.json`",
        "- `docs/final/artifacts/mkm_trackc_client_handoff_package_latest.json`",
        "- `docs/final/artifacts/mkm_trackc_client_handoff_guard_latest.json`",
        "- `docs/final/artifacts/mkm_trackc_operational_acceptance_latest.json`",
        "- `docs/final/artifacts/mkm_trackc_delivery_freeze_log_latest.json`",
        "- `docs/final/artifacts/mkm_trackc_guard_recovery_drill_latest.json`",
        "- `docs/final/artifacts/PADDLE_ONBOARDING_SECURE_RUNBOOK_V1.md`",
        "- `docs/final/artifacts/paddle_onboarding_status_latest.json`",
        "- `docs/final/artifacts/trackc_prophecy_dual_leg_brief_latest.json`",
        "- `docs/final/artifacts/trackc_prophecy_dual_leg_brief_latest.md`",
        "- `docs/final/artifacts/logos_shadow_promotion_status_latest.json`",
        "- `docs/final/artifacts/logos_shadow_insight_latest.json`",
        "- `docs/final/artifacts/logos_semantic_drift_monitor_latest.json`",
        "- `docs/final/artifacts/logos_regime_resonance_shadow_signal_latest.json`",
        "- `docs/final/artifacts/logos_shadow_weekly_gate_latest.json`",
        "- `docs/final/artifacts/logos_shadow_weekly_gate_bootstrap_latest.json`",
        "- `docs/final/artifacts/logos_shadow_weekly_trend_report_latest.json`",
        "- `docs/final/artifacts/logos_shadow_promotion_kpi_progress_latest.json`",
        "- `docs/final/artifacts/logos_response_policy_check_latest.json`",
        "- `docs/final/artifacts/logos_s1_shadow_promotion_review_packet_latest.json`",
        "- `docs/final/artifacts/macro_risk_forward_preregister_lock_latest.json`",
        "- `docs/final/artifacts/macro_risk_forward_log_latest.json`",
        "- `docs/final/artifacts/macro_risk_forward_weekly_report_latest.json`",
    ]
    out_md.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"dashboard json written: {out_json}")
    print(f"dashboard md written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
