from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _lens_music_m32_dashboard_fields(*, hormone_doc: Dict[str, Any], overlay_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Compact M31/M32 audit slice for Track C ops (B-track advisory; no prophecy merge)."""
    ht = hormone_doc.get("gematria_seed_trace")
    ht = ht if isinstance(ht, dict) else {}
    og = (overlay_doc.get("global_state") or {}).get("gematria_seed_trace")
    og = og if isinstance(og, dict) else {}
    present = ht.get("present")
    if present is None:
        present = og.get("present")
    return {
        "gematria_trace_present": bool(present) if present is not None else False,
        "gematria_numeric_value": ht.get("numeric_value", og.get("numeric_value")),
        "gematria_verse_or_token_ref": og.get("verse_or_token_ref") or ht.get("verse_or_token_ref"),
        "gematria_applied_ema_alpha_multiplier": ht.get(
            "applied_ema_alpha_multiplier", og.get("applied_ema_alpha_multiplier")
        ),
        "gematria_effective_hormone_ema_alpha": ht.get(
            "effective_hormone_ema_alpha", og.get("effective_hormone_ema_alpha")
        ),
    }


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


def _build_commercial_kpi_pointers(*, root: Path, art: Path) -> Dict[str, Any]:
    """Lightweight pointers to Track A / P0 commercial SSOT — no revenue math here (Fact-Lock boundary)."""
    ssot_rel = {
        "p0_commercialization_tracker_md": "docs/final/P0_COMMERCIALIZATION_TRACKER.md",
        "track_a_sla_draft_md": "docs/final/TRACK_A_SLA_DRAFT.md",
        "metering_log_jsonl": "reports/constitution/btrack_pilot/track_a_metering_log_v1.jsonl",
        "commercialization_daily_log_jsonl": "reports/track_a_commercialization_daily_log.jsonl",
    }
    art_inputs: Dict[str, Path] = {
        "track_a_metering_summary_latest": art / "track_a_metering_summary_latest.json",
        "track_a_metering_weekly_report_latest": art / "track_a_metering_weekly_report_latest.json",
        "track_a_metering_band_gate_latest": art / "track_a_metering_band_gate_latest.json",
        "track_a_conversational_cost_simulation_latest": art / "track_a_conversational_cost_simulation_latest.json",
        "track_a_shadow_corpus_eval_latest": art / "track_a_shadow_corpus_eval_latest.json",
        "track_a_shadow_corpus_eval_jsonl_sample_latest": art / "track_a_shadow_corpus_eval_jsonl_sample_latest.json",
    }
    ssot_present = {k: (root / v).is_file() for k, v in ssot_rel.items()}
    artifact_present = {k: p.is_file() for k, p in art_inputs.items()}

    weekly = _read_json(art_inputs["track_a_metering_weekly_report_latest"])
    summary = _read_json(art_inputs["track_a_metering_summary_latest"])
    gate = _read_json(art_inputs["track_a_metering_band_gate_latest"])
    cost_sim = _read_json(art_inputs["track_a_conversational_cost_simulation_latest"])
    shadow = _read_json(art_inputs["track_a_shadow_corpus_eval_latest"])

    weekly_snap: Dict[str, Any] = {}
    if weekly:
        weekly_snap = {
            "generated_at_utc": weekly.get("generated_at_utc"),
            "target_band_hit_rate": weekly.get("target_band_hit_rate"),
            "events_in_window": weekly.get("events_in_window"),
        }
    summary_snap: Dict[str, Any] = {}
    if summary:
        summary_snap = {
            "generated_at_utc": summary.get("generated_at_utc"),
            "events_total": summary.get("events_total"),
            "rows": summary.get("rows"),
        }
    gate_snap: Dict[str, Any] = {}
    if gate:
        gate_snap = {
            "generated_at_utc": gate.get("generated_at_utc"),
            "decision": gate.get("decision") or gate.get("status"),
            "gate_mode": gate.get("gate_mode") or gate.get("mode"),
        }
    cost_snap: Dict[str, Any] = {}
    if cost_sim:
        cost_snap = {
            "generated_at_utc": cost_sim.get("generated_at_utc"),
            "status": cost_sim.get("status"),
        }
    shadow_snap: Dict[str, Any] = {}
    if shadow:
        shadow_snap = {
            "generated_at_utc": shadow.get("generated_at_utc"),
            "status": shadow.get("status"),
        }

    return {
        "role": "pointer_only",
        "boundary_note": (
            "Track A commercial KPI evidence lives in P0 paths + artifacts below; "
            "not merged into Track C promotion or B-track lens gates."
        ),
        "ssot": ssot_rel,
        "ssot_present": ssot_present,
        "artifact_paths": {k: str(Path("docs/final/artifacts") / p.name).replace("\\", "/") for k, p in art_inputs.items()},
        "artifact_present": artifact_present,
        "snapshots": {
            "track_a_metering_weekly": weekly_snap,
            "track_a_metering_summary": summary_snap,
            "track_a_metering_band_gate": gate_snap,
            "track_a_conversational_cost_simulation": cost_snap,
            "track_a_shadow_corpus_eval": shadow_snap,
        },
    }


def _tail_agent_decisions_jsonl(path: Path, *, line_tail_budget: int) -> Dict[str, Any]:
    """Last N non-empty lines from append-only agent decisions log (compact fields for dashboard)."""
    rel = "reports/agent_decisions_log.jsonl"
    base: Dict[str, Any] = {
        "source_rel": rel,
        "path_exists": path.is_file(),
        "tail_line_budget": max(0, int(line_tail_budget)),
        "raw_nonempty_lines_in_tail": 0,
        "parsed_ok": 0,
        "parse_errors_in_tail": 0,
        "entries": [],
    }
    if not path.is_file() or base["tail_line_budget"] <= 0:
        return base
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        base["read_error"] = True
        return base
    nonempty = [ln for ln in text.splitlines() if ln.strip()]
    tail = nonempty[-base["tail_line_budget"] :]
    base["raw_nonempty_lines_in_tail"] = len(tail)
    entries: List[Dict[str, Any]] = []
    parse_err = 0
    for line in tail:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            parse_err += 1
            continue
        if not isinstance(obj, dict):
            parse_err += 1
            continue
        ev = obj.get("evidence_path")
        ev_s = None
        if ev is not None:
            ev_s = str(ev).replace("\\", "/")
            if len(ev_s) > 160:
                ev_s = ev_s[:157] + "..."
        entries.append(
            {
                "timestamp": obj.get("timestamp"),
                "mission_id": obj.get("mission_id"),
                "stage": obj.get("stage"),
                "decision": obj.get("decision"),
                "evidence_path": ev_s,
                "actor": obj.get("actor"),
            }
        )
    base["parse_errors_in_tail"] = parse_err
    base["parsed_ok"] = len(entries)
    base["entries"] = entries
    return base


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
    logos_human_approval = _read_json(art / "logos_s1_shadow_promotion_human_approval_latest.json")
    role_router_s1_shadow = _read_json(art / "role_router_s1_shadow_advisory_latest.json")
    fallback_watch = _read_json(art / "fallback_post_cutoff_watch_report_latest.json")
    forward_prereg = _read_json(art / "macro_risk_forward_preregister_lock_latest.json")
    forward_latest = _read_json(art / "macro_risk_forward_log_latest.json")
    forward_weekly = _read_json(art / "macro_risk_forward_weekly_report_latest.json")
    lens_music_audition_governance = _read_json(art / "lens_music_audition_governance_status_latest.json")
    lens_music_prompt_brake_summary = _read_json(art / "lens_music_prompt_brake_history_summary_latest.json")
    lens_music_prompt_brake_trend = _read_json(art / "lens_music_prompt_brake_trend_latest.json")
    lens_music_prompt_poc_metric = _read_json(root / "reports" / "lens_music_prompt_poc_metric_latest.json")
    lens_music_prompt_poc_threshold_recommended = _read_json(
        art / "lens_music_prompt_poc_threshold_recommended_latest.json"
    )
    lens_music_prompt_poc_threshold_drift = _read_json(
        art / "lens_music_prompt_poc_threshold_recommendation_drift_state_latest.json"
    )
    lens_music_prompt_poc_threshold_drift_webhook = _read_json(
        art / "lens_music_prompt_poc_threshold_recommendation_drift_webhook_dispatch_latest.json"
    )
    lens_music_prompt_poc_threshold_watch_rehearsal = _read_json(
        art / "lens_music_prompt_poc_threshold_watch_rehearsal_latest.json"
    )
    mkm_approval_ticket_preflight = _read_json(art / "mkm_approval_ticket_preflight_latest.json")
    lens_music_prompt_poc_threshold_policy = _read_json(art / "lens_music_prompt_poc_threshold_policy_latest.json")
    lens_music_hormone_state = _read_json(root / "reports" / "lens_music_hormone_state_latest.json")
    lens_music_prompt_overlay_latest = _read_json(root / "reports" / "lens_music_prompt_overlay_latest.json")
    lens_music_hormone_trend = _read_json(art / "lens_music_hormone_trend_latest.json")
    lens_music_hormone_trend_webhook = _read_json(art / "lens_music_hormone_trend_webhook_dispatch_latest.json")
    lens_music_promotion_gate = _read_json(root / "reports" / "lens_music_symbolic_audio_promotion_gate_latest.json")
    lens_music_promotion_process = (
        lens_music_promotion_gate["promotion_process"]
        if isinstance(lens_music_promotion_gate.get("promotion_process"), dict)
        else {}
    )
    lens_music_prompt_poc_runbook = _read_json(art / "lens_music_prompt_poc_runbook_latest.json")
    lens_music_prompt_poc_runbook_webhook = _read_json(art / "lens_music_prompt_poc_runbook_webhook_dispatch_latest.json")
    lens_music_prompt_runbook_webhook_health = _read_json(art / "lens_music_prompt_runbook_webhook_health_latest.json")
    forward_health = _forward_pipeline_health(
        prereg=forward_prereg,
        latest=forward_latest,
        weekly=forward_weekly,
        now=now,
    )
    try:
        _tail_n = int(os.environ.get("MKM_AGENT_DECISIONS_LOG_TAIL_N", "24"))
    except ValueError:
        _tail_n = 24
    governance_agent_tail = _tail_agent_decisions_jsonl(
        root / "reports" / "agent_decisions_log.jsonl",
        line_tail_budget=_tail_n,
    )
    commercial_kpi_pointers = _build_commercial_kpi_pointers(root=root, art=art)

    rr_row = role_router_s1_shadow.get("last_row") if isinstance(role_router_s1_shadow.get("last_row"), dict) else {}
    rr_metrics = rr_row.get("metrics") if isinstance(rr_row.get("metrics"), dict) else {}
    lens_music_m32 = _lens_music_m32_dashboard_fields(
        hormone_doc=lens_music_hormone_state,
        overlay_doc=lens_music_prompt_overlay_latest,
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
            "fallback_post_cutoff_watch": {
                "warn_count": ((fallback_watch.get("summary") or {}).get("warn_count")),
                "warn_rate_7d": ((fallback_watch.get("summary") or {}).get("warn_rate_7d")),
                "signal": ((fallback_watch.get("summary") or {}).get("signal")),
                "signal_color": ((fallback_watch.get("summary") or {}).get("signal_color")),
                "latest_warn_ts_utc": ((fallback_watch.get("summary") or {}).get("latest_warn_ts_utc")),
                "days_with_warn": ((fallback_watch.get("summary") or {}).get("days_with_warn")),
            },
            "forward_pipeline_health": forward_health,
            "governance_agent_decisions_tail": governance_agent_tail,
            "lens_music_audition_governance": {
                "state": _status_or_default(lens_music_audition_governance.get("state"), "UNKNOWN"),
                "warn_ratio": lens_music_audition_governance.get("warn_ratio"),
                "warn_ratio_threshold": lens_music_audition_governance.get("warn_ratio_threshold"),
                "warn_count": lens_music_audition_governance.get("warn_count"),
                "sample_count": lens_music_audition_governance.get("sample_count"),
                "generated_at_utc": lens_music_audition_governance.get("generated_at_utc"),
            },
            "lens_music_prompt_brake": {
                "state": _status_or_default(lens_music_prompt_brake_summary.get("state"), "UNKNOWN"),
                "auto_brake_active_rate": lens_music_prompt_brake_summary.get("auto_brake_active_rate"),
                "auto_brake_active_count": lens_music_prompt_brake_summary.get("auto_brake_active_count"),
                "rows_scanned": lens_music_prompt_brake_summary.get("rows_scanned"),
                "trigger_governance_watch_count": ((lens_music_prompt_brake_summary.get("trigger_counts") or {}).get("governance_watch")),
                "trigger_smoke_eval_watch_count": ((lens_music_prompt_brake_summary.get("trigger_counts") or {}).get("smoke_eval_watch")),
                "trend_state": _status_or_default(lens_music_prompt_brake_trend.get("state"), "UNKNOWN"),
                "trend_rows_scanned": lens_music_prompt_brake_trend.get("rows_scanned"),
                "trend_active_rate": lens_music_prompt_brake_trend.get("auto_brake_active_rate"),
                "trend_top_trigger": ((lens_music_prompt_brake_trend.get("top_triggers") or [{}])[0] or {}).get("trigger"),
            },
            "lens_music_prompt_poc_metric": {
                "state": _status_or_default(((lens_music_prompt_poc_metric.get("result") or {}).get("state")), "UNKNOWN"),
                "passed": (lens_music_prompt_poc_metric.get("result") or {}).get("passed"),
                "style_delta_rate": ((lens_music_prompt_poc_metric.get("kpi") or {}).get("style_delta_rate")),
                "overlay_style_match_rate": ((lens_music_prompt_poc_metric.get("kpi") or {}).get("overlay_style_match_rate")),
                "samples_count": lens_music_prompt_poc_metric.get("samples_count"),
            },
            "lens_music_prompt_poc_threshold_recommended": {
                "decision": _status_or_default(lens_music_prompt_poc_threshold_recommended.get("decision"), "UNKNOWN"),
                "min_samples": ((lens_music_prompt_poc_threshold_recommended.get("policy_targets") or {}).get("min_samples")),
                "style_delta_rate_min": (
                    (lens_music_prompt_poc_threshold_recommended.get("policy_targets") or {}).get("style_delta_rate_min")
                ),
                "overlay_style_match_rate_min": (
                    (lens_music_prompt_poc_threshold_recommended.get("policy_targets") or {}).get("overlay_style_match_rate_min")
                ),
            },
            "lens_music_prompt_poc_threshold_drift": {
                "state": _status_or_default(lens_music_prompt_poc_threshold_drift.get("state"), "UNKNOWN"),
                "reason": lens_music_prompt_poc_threshold_drift.get("reason"),
                "min_samples_delta": ((lens_music_prompt_poc_threshold_drift.get("deltas") or {}).get("min_samples_delta")),
                "style_delta_rate_min_delta": (
                    (lens_music_prompt_poc_threshold_drift.get("deltas") or {}).get("style_delta_rate_min_delta")
                ),
                "overlay_style_match_rate_min_delta": (
                    (lens_music_prompt_poc_threshold_drift.get("deltas") or {}).get("overlay_style_match_rate_min_delta")
                ),
            },
            "lens_music_prompt_poc_threshold_drift_webhook": {
                "dispatch_status": ((lens_music_prompt_poc_threshold_drift_webhook.get("dispatch") or {}).get("status")),
                "dispatch_reason": ((lens_music_prompt_poc_threshold_drift_webhook.get("dispatch") or {}).get("reason")),
                "skip_classification": (
                    (lens_music_prompt_poc_threshold_drift_webhook.get("dispatch") or {}).get("skip_classification")
                ),
                "webhook_policy_mode": ((lens_music_prompt_poc_threshold_drift_webhook.get("decision") or {}).get("webhook_policy_mode")),
                "should_dispatch": ((lens_music_prompt_poc_threshold_drift_webhook.get("decision") or {}).get("should_dispatch")),
            },
            "lens_music_prompt_poc_threshold_watch_rehearsal": {
                "strict_mode": lens_music_prompt_poc_threshold_watch_rehearsal.get("strict_mode"),
                "drift_state": lens_music_prompt_poc_threshold_watch_rehearsal.get("drift_state"),
                "dispatch_status": lens_music_prompt_poc_threshold_watch_rehearsal.get("dispatch_status"),
                "dispatch_reason": lens_music_prompt_poc_threshold_watch_rehearsal.get("dispatch_reason"),
                "dispatch_exit_code": lens_music_prompt_poc_threshold_watch_rehearsal.get("dispatch_exit_code"),
            },
            "mkm_approval_ticket_preflight": {
                "decision": _status_or_default(mkm_approval_ticket_preflight.get("decision"), "UNKNOWN"),
                "execution_tag": ((mkm_approval_ticket_preflight.get("inputs") or {}).get("execution_tag")),
                "ticket_id": mkm_approval_ticket_preflight.get("ticket_id"),
                "valid_window_ok": mkm_approval_ticket_preflight.get("valid_window_ok"),
                "reason_count": len(list(mkm_approval_ticket_preflight.get("reasons") or [])),
                "top_reason": (list(mkm_approval_ticket_preflight.get("reasons") or [])[:1] or [None])[0],
            },
            "lens_music_prompt_poc_threshold_policy": {
                "state": _status_or_default(lens_music_prompt_poc_threshold_policy.get("state"), "UNKNOWN"),
                "min_samples": ((lens_music_prompt_poc_threshold_policy.get("policy_targets") or {}).get("min_samples")),
                "style_delta_rate_min": ((lens_music_prompt_poc_threshold_policy.get("policy_targets") or {}).get("style_delta_rate_min")),
                "overlay_style_match_rate_min": ((lens_music_prompt_poc_threshold_policy.get("policy_targets") or {}).get("overlay_style_match_rate_min")),
                "samples_pass": ((lens_music_prompt_poc_threshold_policy.get("checks") or {}).get("samples_pass")),
                "style_delta_pass": ((lens_music_prompt_poc_threshold_policy.get("checks") or {}).get("style_delta_pass")),
                "style_match_pass": ((lens_music_prompt_poc_threshold_policy.get("checks") or {}).get("style_match_pass")),
            },
            "lens_music_hormone_state": {
                "state": _status_or_default(lens_music_hormone_state.get("state"), "UNKNOWN"),
                "stress_index_0_1": lens_music_hormone_state.get("stress_index_0_1"),
                "recovery_buffer_0_1": lens_music_hormone_state.get("recovery_buffer_0_1"),
                "inertia_index_0_1": lens_music_hormone_state.get("inertia_index_0_1"),
                "generated_at_utc": lens_music_hormone_state.get("generated_at_utc"),
                "non_biological_notice": lens_music_hormone_state.get("non_biological_notice"),
                **lens_music_m32,
            },
            "lens_music_hormone_trend": {
                "state": _status_or_default(lens_music_hormone_trend.get("state"), "UNKNOWN"),
                "rows_scanned": lens_music_hormone_trend.get("rows_scanned"),
                "high_stress_rate": lens_music_hormone_trend.get("high_stress_rate"),
                "max_consecutive_high_stress": lens_music_hormone_trend.get("max_consecutive_high_stress"),
                "watch_thresholds": lens_music_hormone_trend.get("watch_thresholds"),
                "operator_hint": lens_music_hormone_trend.get("operator_hint"),
                "mean_rag_metabolism_bounded_drift_0_1": (
                    (lens_music_hormone_trend.get("audit_digest_summary") or {}).get("mean_rag_metabolism_bounded_drift_0_1")
                ),
                "rows_with_rag_drift": (lens_music_hormone_trend.get("audit_digest_summary") or {}).get("rows_with_rag_drift"),
            },
            "lens_music_hormone_trend_webhook": {
                "dispatch_status": ((lens_music_hormone_trend_webhook.get("dispatch") or {}).get("status")),
                "dispatch_reason": ((lens_music_hormone_trend_webhook.get("dispatch") or {}).get("reason")),
                "skip_classification": ((lens_music_hormone_trend_webhook.get("dispatch") or {}).get("skip_classification")),
                "webhook_policy_mode": ((lens_music_hormone_trend_webhook.get("decision") or {}).get("webhook_policy_mode")),
                "dispatch_only_on_watch": ((lens_music_hormone_trend_webhook.get("decision") or {}).get("dispatch_only_on_watch")),
                "should_dispatch": ((lens_music_hormone_trend_webhook.get("decision") or {}).get("should_dispatch")),
            },
            "lens_music_promotion_gate": {
                "decision": _status_or_default(lens_music_promotion_gate.get("decision"), "UNKNOWN"),
                "m31_required_mode": (((lens_music_promotion_gate.get("m31_hormone_guard") or {}).get("guard_mode")) == "required"),
                "m31_guard_mode": ((lens_music_promotion_gate.get("m31_hormone_guard") or {}).get("guard_mode")),
                "m31_guard_passed": ((lens_music_promotion_gate.get("m31_hormone_guard") or {}).get("passed")),
                "commercial_unlock_requested": ((lens_music_promotion_gate.get("commercial_unlock_gate") or {}).get("unlock_requested")),
                "commercial_unlock_applied": ((lens_music_promotion_gate.get("commercial_unlock_gate") or {}).get("unlock_applied")),
                "promotion_process_pass": lens_music_promotion_process.get("process_pass"),
                "promotion_process_exit_code": lens_music_promotion_process.get("process_exit_code"),
                "promotion_gate_m31_profile": (
                    lens_music_promotion_process.get("m31_profile")
                    or ((lens_music_promotion_gate.get("m31_hormone_guard") or {}).get("invocation") or {}).get("profile")
                ),
            },
            "lens_music_prompt_poc_runbook": {
                "state": _status_or_default(lens_music_prompt_poc_runbook.get("state"), "UNKNOWN"),
                "recommendation_count": len(list(lens_music_prompt_poc_runbook.get("recommendations") or [])),
                "top_recommendation_cause": ((lens_music_prompt_poc_runbook.get("recommendations") or [{}])[0] or {}).get("cause"),
            },
            "lens_music_prompt_poc_runbook_webhook": {
                "dispatch_status": ((lens_music_prompt_poc_runbook_webhook.get("dispatch") or {}).get("status")),
                "dispatch_reason": ((lens_music_prompt_poc_runbook_webhook.get("dispatch") or {}).get("reason")),
                "watch_gate_passed": ((lens_music_prompt_poc_runbook_webhook.get("decision") or {}).get("watch_gate_passed")),
                "high_priority_gate_passed": ((lens_music_prompt_poc_runbook_webhook.get("decision") or {}).get("high_priority_gate_passed")),
            },
            "lens_music_prompt_runbook_webhook_health": {
                "state": _status_or_default(lens_music_prompt_runbook_webhook_health.get("state"), "UNKNOWN"),
                "samples_in_window": lens_music_prompt_runbook_webhook_health.get("samples_in_window"),
                "sent_rate": ((lens_music_prompt_runbook_webhook_health.get("rates") or {}).get("sent_rate")),
                "skipped_rate": ((lens_music_prompt_runbook_webhook_health.get("rates") or {}).get("skipped_rate")),
                "failed_rate": ((lens_music_prompt_runbook_webhook_health.get("rates") or {}).get("failed_rate")),
                "top_skip_reason": (
                    (lens_music_prompt_runbook_webhook_health.get("skip_reason_top") or [{}])[0] or {}
                ).get("reason"),
            },
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
                "promotion_human_approval_present": ((logos_human_approval.get("schema") == "logos_s1_shadow_promotion_human_approval_v1")),
                "promotion_human_approval_decision": logos_human_approval.get("decision"),
                "promotion_human_approval_at": logos_human_approval.get("generated_at_utc"),
            },
            "role_router_s1_shadow": {
                "advisory_generated_at_utc": role_router_s1_shadow.get("generated_at_utc"),
                "router_stance": rr_row.get("router_stance"),
                "baseline_stance": rr_row.get("baseline_stance"),
                "baseline_gate_decision": rr_row.get("baseline_gate_decision"),
                "weekly_strict_gap": rr_row.get("weekly_strict_gap"),
                "conflict_resolution_proxy": rr_metrics.get("conflict_resolution_proxy"),
                "false_intervention_proxy": rr_metrics.get("false_intervention_proxy"),
                "router_artifact": rr_row.get("router_artifact"),
            },
        },
        "commercial_kpi_pointers": commercial_kpi_pointers,
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
            "fallback_post_cutoff_watch_report": "docs/final/artifacts/fallback_post_cutoff_watch_report_latest.json",
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
            "logos_s1_shadow_promotion_human_approval": "docs/final/artifacts/logos_s1_shadow_promotion_human_approval_latest.json",
            "role_router_s1_shadow_advisory": "docs/final/artifacts/role_router_s1_shadow_advisory_latest.json",
            "forward_preregister_lock": "docs/final/artifacts/macro_risk_forward_preregister_lock_latest.json",
            "forward_log_latest": "docs/final/artifacts/macro_risk_forward_log_latest.json",
            "forward_weekly_report": "docs/final/artifacts/macro_risk_forward_weekly_report_latest.json",
            "agent_decisions_log": "reports/agent_decisions_log.jsonl",
            "lens_music_audition_governance_status": "docs/final/artifacts/lens_music_audition_governance_status_latest.json",
            "lens_music_prompt_brake_history_summary": "docs/final/artifacts/lens_music_prompt_brake_history_summary_latest.json",
            "lens_music_prompt_brake_trend": "docs/final/artifacts/lens_music_prompt_brake_trend_latest.json",
            "lens_music_prompt_poc_metric": "reports/lens_music_prompt_poc_metric_latest.json",
            "lens_music_prompt_poc_threshold_recommended": "docs/final/artifacts/lens_music_prompt_poc_threshold_recommended_latest.json",
            "lens_music_prompt_poc_threshold_recommendation_drift_state": (
                "docs/final/artifacts/lens_music_prompt_poc_threshold_recommendation_drift_state_latest.json"
            ),
            "lens_music_prompt_poc_threshold_recommendation_drift_webhook_dispatch": (
                "docs/final/artifacts/lens_music_prompt_poc_threshold_recommendation_drift_webhook_dispatch_latest.json"
            ),
            "lens_music_prompt_poc_threshold_watch_rehearsal": (
                "docs/final/artifacts/lens_music_prompt_poc_threshold_watch_rehearsal_latest.json"
            ),
            "mkm_approval_ticket_preflight": "docs/final/artifacts/mkm_approval_ticket_preflight_latest.json",
            "lens_music_prompt_poc_threshold_policy": "docs/final/artifacts/lens_music_prompt_poc_threshold_policy_latest.json",
            "lens_music_symbolic_audio_promotion_gate": "reports/lens_music_symbolic_audio_promotion_gate_latest.json",
            "lens_music_hormone_state": "reports/lens_music_hormone_state_latest.json",
            "lens_music_prompt_overlay_latest": "reports/lens_music_prompt_overlay_latest.json",
            "lens_music_hormone_trend": "docs/final/artifacts/lens_music_hormone_trend_latest.json",
            "lens_music_hormone_trend_webhook_dispatch": "docs/final/artifacts/lens_music_hormone_trend_webhook_dispatch_latest.json",
            "lens_music_prompt_poc_runbook": "docs/final/artifacts/lens_music_prompt_poc_runbook_latest.json",
            "lens_music_prompt_poc_runbook_webhook_dispatch": "docs/final/artifacts/lens_music_prompt_poc_runbook_webhook_dispatch_latest.json",
            "lens_music_prompt_runbook_webhook_health": "docs/final/artifacts/lens_music_prompt_runbook_webhook_health_latest.json",
            "p0_commercialization_tracker": "docs/final/P0_COMMERCIALIZATION_TRACKER.md",
            "track_a_sla_draft": "docs/final/TRACK_A_SLA_DRAFT.md",
            "track_a_metering_log": "reports/constitution/btrack_pilot/track_a_metering_log_v1.jsonl",
            "track_a_commercialization_daily_log": "reports/track_a_commercialization_daily_log.jsonl",
            "track_a_metering_summary_latest": "docs/final/artifacts/track_a_metering_summary_latest.json",
            "track_a_metering_weekly_report_latest": "docs/final/artifacts/track_a_metering_weekly_report_latest.json",
            "track_a_metering_band_gate_latest": "docs/final/artifacts/track_a_metering_band_gate_latest.json",
            "track_a_conversational_cost_simulation_latest": (
                "docs/final/artifacts/track_a_conversational_cost_simulation_latest.json"
            ),
            "track_a_shadow_corpus_eval_latest": "docs/final/artifacts/track_a_shadow_corpus_eval_latest.json",
            "track_a_shadow_corpus_eval_jsonl_sample_latest": (
                "docs/final/artifacts/track_a_shadow_corpus_eval_jsonl_sample_latest.json"
            ),
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
        f"- fallback_post_cutoff_warn_count: `{(dashboard['trackc']['fallback_post_cutoff_watch'] or {}).get('warn_count')}`",
        f"- fallback_post_cutoff_warn_rate_7d: `{(dashboard['trackc']['fallback_post_cutoff_watch'] or {}).get('warn_rate_7d')}`",
        f"- fallback_post_cutoff_signal: `{(dashboard['trackc']['fallback_post_cutoff_watch'] or {}).get('signal')}`",
        f"- fallback_post_cutoff_signal_color: `{(dashboard['trackc']['fallback_post_cutoff_watch'] or {}).get('signal_color')}`",
        f"- fallback_post_cutoff_latest_warn_ts_utc: `{(dashboard['trackc']['fallback_post_cutoff_watch'] or {}).get('latest_warn_ts_utc')}`",
        f"- forward_pipeline_health: `{(dashboard['trackc']['forward_pipeline_health'] or {}).get('status')}`",
        f"- forward_pipeline_reason_codes: `{(dashboard['trackc']['forward_pipeline_health'] or {}).get('reason_codes')}`",
        f"- forward_pipeline_rows_total: `{(dashboard['trackc']['forward_pipeline_health'] or {}).get('rows_total')}`",
        f"- forward_pipeline_rows_in_window_7d: `{(dashboard['trackc']['forward_pipeline_health'] or {}).get('rows_in_window_7d')}`",
        "",
        "## Commercial KPI pointers (Track A / P0 SSOT)",
        f"- role: `{(dashboard.get('commercial_kpi_pointers') or {}).get('role')}`",
        f"- p0_tracker_present: `{(dashboard.get('commercial_kpi_pointers') or {}).get('ssot_present', {}).get('p0_commercialization_tracker_md')}`",
        f"- track_a_metering_weekly_present: `{(dashboard.get('commercial_kpi_pointers') or {}).get('artifact_present', {}).get('track_a_metering_weekly_report_latest')}`",
        f"- weekly_target_band_hit_rate: `{((dashboard.get('commercial_kpi_pointers') or {}).get('snapshots') or {}).get('track_a_metering_weekly', {}).get('target_band_hit_rate')}`",
        f"- weekly_events_in_window: `{((dashboard.get('commercial_kpi_pointers') or {}).get('snapshots') or {}).get('track_a_metering_weekly', {}).get('events_in_window')}`",
        f"- band_gate_decision: `{((dashboard.get('commercial_kpi_pointers') or {}).get('snapshots') or {}).get('track_a_metering_band_gate', {}).get('decision')}`",
        "",
        "## Governance audit tail (`reports/agent_decisions_log.jsonl`)",
        f"- path_exists: `{(dashboard['trackc'].get('governance_agent_decisions_tail') or {}).get('path_exists')}`",
        f"- tail_line_budget: `{(dashboard['trackc'].get('governance_agent_decisions_tail') or {}).get('tail_line_budget')}`",
        f"- parsed_ok: `{(dashboard['trackc'].get('governance_agent_decisions_tail') or {}).get('parsed_ok')}`",
        f"- parse_errors_in_tail: `{(dashboard['trackc'].get('governance_agent_decisions_tail') or {}).get('parse_errors_in_tail')}`",
    ]
    _gtail = dashboard["trackc"].get("governance_agent_decisions_tail") or {}
    _gentries = list(_gtail.get("entries") or [])
    for row in _gentries[-8:]:
        ts = row.get("timestamp")
        mid = row.get("mission_id")
        dec = row.get("decision")
        stg = row.get("stage")
        md.append(f"- `{ts}` | `{mid}` | `{stg}` | `{dec}`")
    md.extend(
        [
        f"- lens_music_audition_governance_state: `{(dashboard['trackc']['lens_music_audition_governance'] or {}).get('state')}`",
        f"- lens_music_audition_warn_ratio: `{(dashboard['trackc']['lens_music_audition_governance'] or {}).get('warn_ratio')}`",
        f"- lens_music_audition_warn_ratio_threshold: `{(dashboard['trackc']['lens_music_audition_governance'] or {}).get('warn_ratio_threshold')}`",
        f"- lens_music_audition_warn_count: `{(dashboard['trackc']['lens_music_audition_governance'] or {}).get('warn_count')}`",
        f"- lens_music_audition_sample_count: `{(dashboard['trackc']['lens_music_audition_governance'] or {}).get('sample_count')}`",
        f"- lens_music_prompt_brake_state: `{(dashboard['trackc']['lens_music_prompt_brake'] or {}).get('state')}`",
        f"- lens_music_prompt_brake_active_rate: `{(dashboard['trackc']['lens_music_prompt_brake'] or {}).get('auto_brake_active_rate')}`",
        f"- lens_music_prompt_brake_active_count: `{(dashboard['trackc']['lens_music_prompt_brake'] or {}).get('auto_brake_active_count')}`",
        f"- lens_music_prompt_brake_rows_scanned: `{(dashboard['trackc']['lens_music_prompt_brake'] or {}).get('rows_scanned')}`",
        f"- lens_music_prompt_brake_trend_state: `{(dashboard['trackc']['lens_music_prompt_brake'] or {}).get('trend_state')}`",
        f"- lens_music_prompt_brake_trend_active_rate: `{(dashboard['trackc']['lens_music_prompt_brake'] or {}).get('trend_active_rate')}`",
        f"- lens_music_prompt_brake_trend_top_trigger: `{(dashboard['trackc']['lens_music_prompt_brake'] or {}).get('trend_top_trigger')}`",
        f"- lens_music_prompt_poc_state: `{(dashboard['trackc']['lens_music_prompt_poc_metric'] or {}).get('state')}`",
        f"- lens_music_prompt_poc_passed: `{(dashboard['trackc']['lens_music_prompt_poc_metric'] or {}).get('passed')}`",
        f"- lens_music_prompt_poc_style_delta_rate: `{(dashboard['trackc']['lens_music_prompt_poc_metric'] or {}).get('style_delta_rate')}`",
        f"- lens_music_prompt_poc_style_match_rate: `{(dashboard['trackc']['lens_music_prompt_poc_metric'] or {}).get('overlay_style_match_rate')}`",
        f"- lens_music_prompt_poc_threshold_recommended_decision: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_recommended'] or {}).get('decision')}`",
        f"- lens_music_prompt_poc_threshold_recommended_min_samples: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_recommended'] or {}).get('min_samples')}`",
        f"- lens_music_prompt_poc_threshold_recommended_style_delta_min: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_recommended'] or {}).get('style_delta_rate_min')}`",
        f"- lens_music_prompt_poc_threshold_recommended_style_match_min: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_recommended'] or {}).get('overlay_style_match_rate_min')}`",
        f"- lens_music_prompt_poc_threshold_drift_state: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_drift'] or {}).get('state')}`",
        f"- lens_music_prompt_poc_threshold_drift_reason: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_drift'] or {}).get('reason')}`",
        f"- lens_music_prompt_poc_threshold_drift_min_samples_delta: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_drift'] or {}).get('min_samples_delta')}`",
        f"- lens_music_prompt_poc_threshold_drift_style_delta_min_delta: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_drift'] or {}).get('style_delta_rate_min_delta')}`",
        f"- lens_music_prompt_poc_threshold_drift_style_match_min_delta: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_drift'] or {}).get('overlay_style_match_rate_min_delta')}`",
        f"- lens_music_prompt_poc_threshold_drift_webhook_status: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_drift_webhook'] or {}).get('dispatch_status')}`",
        f"- lens_music_prompt_poc_threshold_drift_webhook_reason: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_drift_webhook'] or {}).get('dispatch_reason')}`",
        f"- lens_music_prompt_poc_threshold_drift_webhook_skip_classification: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_drift_webhook'] or {}).get('skip_classification')}`",
        f"- lens_music_prompt_poc_threshold_drift_webhook_policy_mode: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_drift_webhook'] or {}).get('webhook_policy_mode')}`",
        f"- lens_music_prompt_poc_threshold_drift_webhook_should_dispatch: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_drift_webhook'] or {}).get('should_dispatch')}`",
        f"- lens_music_prompt_poc_threshold_watch_rehearsal_strict_mode: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_watch_rehearsal'] or {}).get('strict_mode')}`",
        f"- lens_music_prompt_poc_threshold_watch_rehearsal_drift_state: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_watch_rehearsal'] or {}).get('drift_state')}`",
        f"- lens_music_prompt_poc_threshold_watch_rehearsal_dispatch_status: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_watch_rehearsal'] or {}).get('dispatch_status')}`",
        f"- lens_music_prompt_poc_threshold_watch_rehearsal_dispatch_reason: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_watch_rehearsal'] or {}).get('dispatch_reason')}`",
        f"- lens_music_prompt_poc_threshold_watch_rehearsal_dispatch_exit_code: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_watch_rehearsal'] or {}).get('dispatch_exit_code')}`",
        f"- mkm_approval_ticket_preflight_decision: `{(dashboard['trackc']['mkm_approval_ticket_preflight'] or {}).get('decision')}`",
        f"- mkm_approval_ticket_preflight_execution_tag: `{(dashboard['trackc']['mkm_approval_ticket_preflight'] or {}).get('execution_tag')}`",
        f"- mkm_approval_ticket_preflight_ticket_id: `{(dashboard['trackc']['mkm_approval_ticket_preflight'] or {}).get('ticket_id')}`",
        f"- mkm_approval_ticket_preflight_valid_window_ok: `{(dashboard['trackc']['mkm_approval_ticket_preflight'] or {}).get('valid_window_ok')}`",
        f"- mkm_approval_ticket_preflight_top_reason: `{(dashboard['trackc']['mkm_approval_ticket_preflight'] or {}).get('top_reason')}`",
        f"- lens_music_prompt_poc_threshold_policy_state: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_policy'] or {}).get('state')}`",
        f"- lens_music_prompt_poc_threshold_min_samples: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_policy'] or {}).get('min_samples')}`",
        f"- lens_music_prompt_poc_threshold_style_delta_min: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_policy'] or {}).get('style_delta_rate_min')}`",
        f"- lens_music_prompt_poc_threshold_style_match_min: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_policy'] or {}).get('overlay_style_match_rate_min')}`",
        f"- lens_music_prompt_poc_threshold_samples_pass: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_policy'] or {}).get('samples_pass')}`",
        f"- lens_music_prompt_poc_threshold_style_delta_pass: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_policy'] or {}).get('style_delta_pass')}`",
        f"- lens_music_prompt_poc_threshold_style_match_pass: `{(dashboard['trackc']['lens_music_prompt_poc_threshold_policy'] or {}).get('style_match_pass')}`",
        f"- lens_music_hormone_state: `{(dashboard['trackc']['lens_music_hormone_state'] or {}).get('state')}`",
        f"- lens_music_hormone_stress_index_0_1: `{(dashboard['trackc']['lens_music_hormone_state'] or {}).get('stress_index_0_1')}`",
        f"- lens_music_hormone_recovery_buffer_0_1: `{(dashboard['trackc']['lens_music_hormone_state'] or {}).get('recovery_buffer_0_1')}`",
        f"- lens_music_hormone_inertia_index_0_1: `{(dashboard['trackc']['lens_music_hormone_state'] or {}).get('inertia_index_0_1')}`",
        f"- lens_music_gematria_trace_present: `{(dashboard['trackc']['lens_music_hormone_state'] or {}).get('gematria_trace_present')}`",
        f"- lens_music_gematria_verse_or_token_ref: `{(dashboard['trackc']['lens_music_hormone_state'] or {}).get('gematria_verse_or_token_ref')}`",
        f"- lens_music_gematria_numeric_value: `{(dashboard['trackc']['lens_music_hormone_state'] or {}).get('gematria_numeric_value')}`",
        f"- lens_music_gematria_applied_ema_alpha_multiplier: `{(dashboard['trackc']['lens_music_hormone_state'] or {}).get('gematria_applied_ema_alpha_multiplier')}`",
        f"- lens_music_gematria_effective_hormone_ema_alpha: `{(dashboard['trackc']['lens_music_hormone_state'] or {}).get('gematria_effective_hormone_ema_alpha')}`",
        f"- lens_music_hormone_trend_state: `{(dashboard['trackc']['lens_music_hormone_trend'] or {}).get('state')}`",
        f"- lens_music_hormone_trend_high_stress_rate: `{(dashboard['trackc']['lens_music_hormone_trend'] or {}).get('high_stress_rate')}`",
        f"- lens_music_hormone_trend_max_consecutive_high_stress: `{(dashboard['trackc']['lens_music_hormone_trend'] or {}).get('max_consecutive_high_stress')}`",
        f"- lens_music_hormone_trend_operator_hint: `{(dashboard['trackc']['lens_music_hormone_trend'] or {}).get('operator_hint')}`",
        f"- lens_music_hormone_trend_webhook_status: `{(dashboard['trackc']['lens_music_hormone_trend_webhook'] or {}).get('dispatch_status')}`",
        f"- lens_music_hormone_trend_webhook_reason: `{(dashboard['trackc']['lens_music_hormone_trend_webhook'] or {}).get('dispatch_reason')}`",
        f"- lens_music_hormone_trend_webhook_skip_classification: `{(dashboard['trackc']['lens_music_hormone_trend_webhook'] or {}).get('skip_classification')}`",
        f"- lens_music_hormone_trend_webhook_policy_mode: `{(dashboard['trackc']['lens_music_hormone_trend_webhook'] or {}).get('webhook_policy_mode')}`",
        f"- lens_music_promotion_gate_decision: `{(dashboard['trackc']['lens_music_promotion_gate'] or {}).get('decision')}`",
        f"- lens_music_m31_required_mode: `{(dashboard['trackc']['lens_music_promotion_gate'] or {}).get('m31_required_mode')}`",
        f"- lens_music_m31_guard_mode: `{(dashboard['trackc']['lens_music_promotion_gate'] or {}).get('m31_guard_mode')}`",
        f"- lens_music_m31_guard_passed: `{(dashboard['trackc']['lens_music_promotion_gate'] or {}).get('m31_guard_passed')}`",
        f"- lens_music_commercial_unlock_requested: `{(dashboard['trackc']['lens_music_promotion_gate'] or {}).get('commercial_unlock_requested')}`",
        f"- lens_music_commercial_unlock_applied: `{(dashboard['trackc']['lens_music_promotion_gate'] or {}).get('commercial_unlock_applied')}`",
        f"- lens_music_promotion_process_pass: `{(dashboard['trackc']['lens_music_promotion_gate'] or {}).get('promotion_process_pass')}`",
        f"- lens_music_promotion_process_exit_code: `{(dashboard['trackc']['lens_music_promotion_gate'] or {}).get('promotion_process_exit_code')}`",
        f"- lens_music_promotion_gate_m31_profile: `{(dashboard['trackc']['lens_music_promotion_gate'] or {}).get('promotion_gate_m31_profile')}`",
        f"- lens_music_prompt_poc_runbook_state: `{(dashboard['trackc']['lens_music_prompt_poc_runbook'] or {}).get('state')}`",
        f"- lens_music_prompt_poc_runbook_recommendation_count: `{(dashboard['trackc']['lens_music_prompt_poc_runbook'] or {}).get('recommendation_count')}`",
        f"- lens_music_prompt_poc_runbook_top_cause: `{(dashboard['trackc']['lens_music_prompt_poc_runbook'] or {}).get('top_recommendation_cause')}`",
        f"- lens_music_prompt_poc_runbook_webhook_status: `{(dashboard['trackc']['lens_music_prompt_poc_runbook_webhook'] or {}).get('dispatch_status')}`",
        f"- lens_music_prompt_poc_runbook_webhook_reason: `{(dashboard['trackc']['lens_music_prompt_poc_runbook_webhook'] or {}).get('dispatch_reason')}`",
        f"- lens_music_prompt_runbook_webhook_health_state: `{(dashboard['trackc']['lens_music_prompt_runbook_webhook_health'] or {}).get('state')}`",
        f"- lens_music_prompt_runbook_webhook_health_samples: `{(dashboard['trackc']['lens_music_prompt_runbook_webhook_health'] or {}).get('samples_in_window')}`",
        f"- lens_music_prompt_runbook_webhook_sent_rate: `{(dashboard['trackc']['lens_music_prompt_runbook_webhook_health'] or {}).get('sent_rate')}`",
        f"- lens_music_prompt_runbook_webhook_skipped_rate: `{(dashboard['trackc']['lens_music_prompt_runbook_webhook_health'] or {}).get('skipped_rate')}`",
        f"- lens_music_prompt_runbook_webhook_top_skip_reason: `{(dashboard['trackc']['lens_music_prompt_runbook_webhook_health'] or {}).get('top_skip_reason')}`",
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
        f"- promotion_human_approval_present: `{((dashboard['trackc']['logos_shadow'] or {}).get('promotion_human_approval_present'))}`",
        f"- promotion_human_approval_decision: `{((dashboard['trackc']['logos_shadow'] or {}).get('promotion_human_approval_decision'))}`",
        f"- promotion_human_approval_at: `{((dashboard['trackc']['logos_shadow'] or {}).get('promotion_human_approval_at'))}`",
        "",
        "## Role router S1 shadow (advisory, non-gating)",
        f"- advisory_generated_at_utc: `{(dashboard['trackc'].get('role_router_s1_shadow') or {}).get('advisory_generated_at_utc')}`",
        f"- router_stance: `{(dashboard['trackc'].get('role_router_s1_shadow') or {}).get('router_stance')}`",
        f"- baseline_stance: `{(dashboard['trackc'].get('role_router_s1_shadow') or {}).get('baseline_stance')}`",
        f"- baseline_gate_decision: `{(dashboard['trackc'].get('role_router_s1_shadow') or {}).get('baseline_gate_decision')}`",
        f"- weekly_strict_gap: `{(dashboard['trackc'].get('role_router_s1_shadow') or {}).get('weekly_strict_gap')}`",
        f"- conflict_resolution_proxy: `{(dashboard['trackc'].get('role_router_s1_shadow') or {}).get('conflict_resolution_proxy')}`",
        f"- false_intervention_proxy: `{(dashboard['trackc'].get('role_router_s1_shadow') or {}).get('false_intervention_proxy')}`",
        f"- router_artifact: `{(dashboard['trackc'].get('role_router_s1_shadow') or {}).get('router_artifact')}`",
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
        "- `docs/final/artifacts/fallback_post_cutoff_watch_report_latest.json`",
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
        "- `docs/final/artifacts/logos_s1_shadow_promotion_human_approval_latest.json`",
        "- `docs/final/artifacts/role_router_s1_shadow_advisory_latest.json`",
        "- `docs/final/artifacts/macro_risk_forward_preregister_lock_latest.json`",
        "- `docs/final/artifacts/macro_risk_forward_log_latest.json`",
        "- `docs/final/artifacts/macro_risk_forward_weekly_report_latest.json`",
        "- `docs/final/artifacts/lens_music_audition_governance_status_latest.json`",
        "- `docs/final/artifacts/lens_music_prompt_brake_history_summary_latest.json`",
        "- `docs/final/artifacts/lens_music_prompt_brake_trend_latest.json`",
        "- `reports/lens_music_prompt_poc_metric_latest.json`",
        "- `docs/final/artifacts/lens_music_prompt_poc_runbook_latest.json`",
        "- `docs/final/artifacts/lens_music_prompt_poc_runbook_webhook_dispatch_latest.json`",
        "- `docs/final/artifacts/lens_music_prompt_runbook_webhook_health_latest.json`",
        "- `reports/agent_decisions_log.jsonl`",
        "- `docs/final/P0_COMMERCIALIZATION_TRACKER.md`",
        "- `docs/final/TRACK_A_SLA_DRAFT.md`",
        "- `reports/constitution/btrack_pilot/track_a_metering_log_v1.jsonl`",
        "- `reports/track_a_commercialization_daily_log.jsonl`",
        "- `docs/final/artifacts/track_a_metering_summary_latest.json`",
        "- `docs/final/artifacts/track_a_metering_weekly_report_latest.json`",
        "- `docs/final/artifacts/track_a_metering_band_gate_latest.json`",
        "- `docs/final/artifacts/track_a_conversational_cost_simulation_latest.json`",
        "- `docs/final/artifacts/track_a_shadow_corpus_eval_latest.json`",
        "- `docs/final/artifacts/track_a_shadow_corpus_eval_jsonl_sample_latest.json`",
        ]
    )
    out_md.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"dashboard json written: {out_json}")
    print(f"dashboard md written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
