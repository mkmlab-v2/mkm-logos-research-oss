#!/usr/bin/env python3
"""Build one-file unified dashboard for Cursor AI operations."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_WEEKLY = ART / "layer1_layer5_weekly_ops_report_latest.json"
DEFAULT_PREFLIGHT = ART / "emotion_state_live_preflight_gate_latest.json"
DEFAULT_MEMORY_VALIDATION = ART / "agent_memory_validation_latest.json"
DEFAULT_MEMORY_REBUILD = ART / "agent_memory_weekly_rebuild_summary_latest.json"
DEFAULT_STREAK = ART / "layer1_layer5_weekly_streak_gate_latest.json"
DEFAULT_MICROCOSM_RUNTIME = ART / "sasang_microcosm_runtime_assessment_latest.json"
DEFAULT_GENIUS_BENCHMARK = ART / "genius_reasoning_benchmark_report_latest.json"
DEFAULT_GENIUS_ALERT = ART / "genius_reasoning_benchmark_alert_latest.json"
DEFAULT_GENIUS_ALERT_TREND = ART / "genius_reasoning_benchmark_alert_trend_gate_latest.json"
DEFAULT_GENIUS_HUMAN_REVIEW_GATE = ART / "genius_reasoning_human_review_gate_latest.json"
DEFAULT_GENIUS_HUMAN_REVIEW_DISPATCH = ART / "genius_reasoning_human_review_gate_dispatch_latest.json"
DEFAULT_GENIUS_HUMAN_REVIEW_TREND = ART / "genius_reasoning_human_review_gate_trend_latest.json"
DEFAULT_GENIUS_HUMAN_REVIEW_TREND_DISPATCH = ART / "genius_reasoning_human_review_gate_trend_dispatch_latest.json"
DEFAULT_GENIUS_DISPATCH_HEALTH_GATE = ART / "genius_reasoning_dispatch_health_gate_latest.json"
DEFAULT_GENIUS_DISPATCH_HEALTH_GATE_DISPATCH = ART / "genius_reasoning_dispatch_health_gate_dispatch_latest.json"
DEFAULT_BLEND_RUNTIME = ART / "symbolic_reality_blend_runtime_latest.json"
DEFAULT_ANCHOR_TIERING = ART / "external_bible_anchor_tiering_latest.json"
DEFAULT_ANCHOR_REHEARSAL = ART / "external_bible_anchor_adopt_limited_rehearsal_latest.json"
DEFAULT_ANCHOR_SHADOW = ART / "external_bible_anchor_shadow_rehearsal_latest.json"
DEFAULT_ANCHOR_PROMOTION = ART / "external_bible_anchor_tier1_promotion_candidates_latest.json"
DEFAULT_ANCHOR_PROMOTED = ART / "external_bible_anchor_tier1_promoted_latest.json"
DEFAULT_ANCHOR_SUSTAIN = ART / "external_bible_anchor_promotion_sustain_gate_latest.json"
DEFAULT_ANCHOR_RECOVERY = ART / "external_bible_anchor_recovery_candidates_latest.json"
DEFAULT_ANCHOR_DRILL = ART / "external_bible_anchor_downgrade_recovery_drill_latest.json"
DEFAULT_ANCHOR_WEEKLY_AB = ART / "external_bible_anchor_weekly_ab_report_latest.json"
DEFAULT_ANCHOR_POLICY_STAGE_DRILL = ART / "external_bible_anchor_policy_stage_drill_latest.json"
DEFAULT_ANCHOR_HANDOFF = ART / "external_bible_anchor_promotion_handoff_packet_latest.json"
DEFAULT_OUT = ART / "cursor_ai_unified_status_dashboard_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--weekly-report-json", type=Path, default=DEFAULT_WEEKLY)
    ap.add_argument("--preflight-json", type=Path, default=DEFAULT_PREFLIGHT)
    ap.add_argument("--memory-validation-json", type=Path, default=DEFAULT_MEMORY_VALIDATION)
    ap.add_argument("--memory-rebuild-json", type=Path, default=DEFAULT_MEMORY_REBUILD)
    ap.add_argument("--streak-gate-json", type=Path, default=DEFAULT_STREAK)
    ap.add_argument("--microcosm-runtime-json", type=Path, default=DEFAULT_MICROCOSM_RUNTIME)
    ap.add_argument("--genius-benchmark-json", type=Path, default=DEFAULT_GENIUS_BENCHMARK)
    ap.add_argument("--genius-alert-json", type=Path, default=DEFAULT_GENIUS_ALERT)
    ap.add_argument("--genius-alert-trend-json", type=Path, default=DEFAULT_GENIUS_ALERT_TREND)
    ap.add_argument("--genius-human-review-gate-json", type=Path, default=DEFAULT_GENIUS_HUMAN_REVIEW_GATE)
    ap.add_argument("--genius-human-review-dispatch-json", type=Path, default=DEFAULT_GENIUS_HUMAN_REVIEW_DISPATCH)
    ap.add_argument("--genius-human-review-trend-json", type=Path, default=DEFAULT_GENIUS_HUMAN_REVIEW_TREND)
    ap.add_argument("--genius-human-review-trend-dispatch-json", type=Path, default=DEFAULT_GENIUS_HUMAN_REVIEW_TREND_DISPATCH)
    ap.add_argument("--genius-dispatch-health-gate-json", type=Path, default=DEFAULT_GENIUS_DISPATCH_HEALTH_GATE)
    ap.add_argument("--genius-dispatch-health-gate-dispatch-json", type=Path, default=DEFAULT_GENIUS_DISPATCH_HEALTH_GATE_DISPATCH)
    ap.add_argument("--blend-runtime-json", type=Path, default=DEFAULT_BLEND_RUNTIME)
    ap.add_argument("--anchor-tiering-json", type=Path, default=DEFAULT_ANCHOR_TIERING)
    ap.add_argument("--anchor-rehearsal-json", type=Path, default=DEFAULT_ANCHOR_REHEARSAL)
    ap.add_argument("--anchor-shadow-json", type=Path, default=DEFAULT_ANCHOR_SHADOW)
    ap.add_argument("--anchor-promotion-json", type=Path, default=DEFAULT_ANCHOR_PROMOTION)
    ap.add_argument("--anchor-promoted-json", type=Path, default=DEFAULT_ANCHOR_PROMOTED)
    ap.add_argument("--anchor-sustain-json", type=Path, default=DEFAULT_ANCHOR_SUSTAIN)
    ap.add_argument("--anchor-recovery-json", type=Path, default=DEFAULT_ANCHOR_RECOVERY)
    ap.add_argument("--anchor-drill-json", type=Path, default=DEFAULT_ANCHOR_DRILL)
    ap.add_argument("--anchor-weekly-ab-json", type=Path, default=DEFAULT_ANCHOR_WEEKLY_AB)
    ap.add_argument("--anchor-policy-stage-drill-json", type=Path, default=DEFAULT_ANCHOR_POLICY_STAGE_DRILL)
    ap.add_argument("--anchor-handoff-json", type=Path, default=DEFAULT_ANCHOR_HANDOFF)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    weekly = _read_json(args.weekly_report_json)
    preflight = _read_json(args.preflight_json)
    mem_val = _read_json(args.memory_validation_json)
    mem_rebuild = _read_json(args.memory_rebuild_json)
    streak = _read_json(args.streak_gate_json)
    microcosm = _read_json(args.microcosm_runtime_json)
    genius_benchmark = _read_json(args.genius_benchmark_json)
    genius_alert = _read_json(args.genius_alert_json)
    genius_alert_trend = _read_json(args.genius_alert_trend_json)
    genius_human_review_gate = _read_json(args.genius_human_review_gate_json)
    genius_human_review_dispatch = _read_json(args.genius_human_review_dispatch_json)
    genius_human_review_trend = _read_json(args.genius_human_review_trend_json)
    genius_human_review_trend_dispatch = _read_json(args.genius_human_review_trend_dispatch_json)
    genius_dispatch_health_gate = _read_json(args.genius_dispatch_health_gate_json)
    genius_dispatch_health_gate_dispatch = _read_json(args.genius_dispatch_health_gate_dispatch_json)
    blend = _read_json(args.blend_runtime_json)
    anchor_tiering = _read_json(args.anchor_tiering_json)
    anchor_rehearsal = _read_json(args.anchor_rehearsal_json)
    anchor_shadow = _read_json(args.anchor_shadow_json)
    anchor_promotion = _read_json(args.anchor_promotion_json)
    anchor_promoted = _read_json(args.anchor_promoted_json)
    anchor_sustain = _read_json(args.anchor_sustain_json)
    anchor_recovery = _read_json(args.anchor_recovery_json)
    anchor_drill = _read_json(args.anchor_drill_json)
    anchor_weekly_ab = _read_json(args.anchor_weekly_ab_json)
    anchor_policy_stage_drill = _read_json(args.anchor_policy_stage_drill_json)
    anchor_handoff = _read_json(args.anchor_handoff_json)

    weekly_status = str(weekly.get("overall_status") or "UNKNOWN")
    preflight_decision = str(preflight.get("decision") or "UNKNOWN")
    memory_status = str(mem_val.get("status") or "UNKNOWN")
    streak_status = str(streak.get("status") or "UNKNOWN")
    genius_status = str((genius_benchmark.get("summary") or {}).get("benchmark_status") or "UNKNOWN")
    genius_robust_status = str((genius_benchmark.get("robustness") or {}).get("robust_benchmark_status") or "UNKNOWN")
    genius_subscore_pass = bool((genius_benchmark.get("subscores") or {}).get("subscore_gate_pass"))
    genius_alert_trend_status = str(genius_alert_trend.get("status") or "UNKNOWN")
    genius_human_review_status = str(genius_human_review_gate.get("status") or "UNKNOWN")
    genius_human_review_trend_status = str(genius_human_review_trend.get("status") or "UNKNOWN")
    genius_dispatch_health_status = str(genius_dispatch_health_gate.get("status") or "UNKNOWN")

    go = (
        weekly_status == "PASS"
        and preflight_decision == "GO_LIVE_CANDIDATE"
        and memory_status == "PASS"
        and streak_status == "PASS"
        and genius_status == "PASS"
        and genius_robust_status == "PASS"
        and genius_subscore_pass
        and genius_alert_trend_status == "PASS"
        and genius_human_review_status == "PASS"
        and genius_human_review_trend_status == "PASS"
        and genius_dispatch_health_status == "PASS"
    )

    out = {
        "schema": "cursor_ai_unified_status_dashboard_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "weekly_report_json": str(args.weekly_report_json).replace("\\", "/"),
            "preflight_json": str(args.preflight_json).replace("\\", "/"),
            "memory_validation_json": str(args.memory_validation_json).replace("\\", "/"),
            "memory_rebuild_json": str(args.memory_rebuild_json).replace("\\", "/"),
            "streak_gate_json": str(args.streak_gate_json).replace("\\", "/"),
            "microcosm_runtime_json": str(args.microcosm_runtime_json).replace("\\", "/"),
            "genius_benchmark_json": str(args.genius_benchmark_json).replace("\\", "/"),
            "genius_alert_json": str(args.genius_alert_json).replace("\\", "/"),
            "genius_alert_trend_json": str(args.genius_alert_trend_json).replace("\\", "/"),
            "genius_human_review_gate_json": str(args.genius_human_review_gate_json).replace("\\", "/"),
            "genius_human_review_dispatch_json": str(args.genius_human_review_dispatch_json).replace("\\", "/"),
            "genius_human_review_trend_json": str(args.genius_human_review_trend_json).replace("\\", "/"),
            "genius_human_review_trend_dispatch_json": str(args.genius_human_review_trend_dispatch_json).replace("\\", "/"),
            "genius_dispatch_health_gate_json": str(args.genius_dispatch_health_gate_json).replace("\\", "/"),
            "genius_dispatch_health_gate_dispatch_json": str(args.genius_dispatch_health_gate_dispatch_json).replace("\\", "/"),
            "blend_runtime_json": str(args.blend_runtime_json).replace("\\", "/"),
            "anchor_tiering_json": str(args.anchor_tiering_json).replace("\\", "/"),
            "anchor_rehearsal_json": str(args.anchor_rehearsal_json).replace("\\", "/"),
            "anchor_shadow_json": str(args.anchor_shadow_json).replace("\\", "/"),
            "anchor_promotion_json": str(args.anchor_promotion_json).replace("\\", "/"),
            "anchor_promoted_json": str(args.anchor_promoted_json).replace("\\", "/"),
            "anchor_sustain_json": str(args.anchor_sustain_json).replace("\\", "/"),
            "anchor_recovery_json": str(args.anchor_recovery_json).replace("\\", "/"),
            "anchor_drill_json": str(args.anchor_drill_json).replace("\\", "/"),
            "anchor_weekly_ab_json": str(args.anchor_weekly_ab_json).replace("\\", "/"),
            "anchor_policy_stage_drill_json": str(args.anchor_policy_stage_drill_json).replace("\\", "/"),
            "anchor_handoff_json": str(args.anchor_handoff_json).replace("\\", "/"),
        },
        "status": "GO" if go else "HOLD",
        "summary": {
            "weekly_overall_status": weekly_status,
            "preflight_decision": preflight_decision,
            "memory_validation_status": memory_status,
            "memory_hot_rows": mem_rebuild.get("hot_rows"),
            "memory_cooled_rows": mem_rebuild.get("cooled_rows"),
            "streak_gate_status": streak_status,
            "streak_pass_count": ((streak.get("current") or {}).get("pass_streak")),
            "streak_preflight_go_count": ((streak.get("current") or {}).get("preflight_go_streak")),
            "microcosm_stage": ((microcosm.get("diagnosis") or {}).get("stage")),
            "microcosm_risk_band": ((microcosm.get("diagnosis") or {}).get("risk_band")),
            "microcosm_tau_prime": ((microcosm.get("derived") or {}).get("tau_prime")),
            "genius_benchmark_status": genius_status,
            "genius_weighted_score_100": ((genius_benchmark.get("summary") or {}).get("weighted_score_100")),
            "genius_robust_benchmark_status": genius_robust_status,
            "genius_robust_score_100": ((genius_benchmark.get("robustness") or {}).get("robust_score_100")),
            "genius_human_coverage": ((genius_benchmark.get("robustness") or {}).get("human_coverage")),
            "genius_calibration_gap": ((genius_benchmark.get("robustness") or {}).get("calibration_gap")),
            "genius_freshness_gate_pass": ((genius_benchmark.get("robustness") or {}).get("freshness_gate_pass")),
            "genius_stale_approved_count": ((genius_benchmark.get("robustness") or {}).get("stale_approved_count")),
            "genius_max_approved_label_age_days": ((genius_benchmark.get("robustness") or {}).get("max_approved_label_age_days")),
            "genius_alert_active": ((genius_alert.get("alert") or {}).get("active")),
            "genius_alert_severity": ((genius_alert.get("alert") or {}).get("severity")),
            "genius_alert_reasons": ((genius_alert.get("alert") or {}).get("reasons")),
            "genius_general_score": ((genius_benchmark.get("subscores") or {}).get("general_score")),
            "genius_safety_score": ((genius_benchmark.get("subscores") or {}).get("safety_score")),
            "genius_long_horizon_score": ((genius_benchmark.get("subscores") or {}).get("long_horizon_score")),
            "genius_subscore_gate_pass": genius_subscore_pass,
            "genius_alert_trend_status": genius_alert_trend_status,
            "genius_alert_trend_reasons": genius_alert_trend.get("reasons"),
            "genius_human_review_gate_status": genius_human_review_status,
            "genius_human_review_gate_reasons": genius_human_review_gate.get("reasons"),
            "genius_human_pending_rows": ((genius_human_review_gate.get("current") or {}).get("pending_rows")),
            "genius_human_pending_ratio": ((genius_human_review_gate.get("current") or {}).get("pending_ratio")),
            "genius_human_review_dispatch_status": ((genius_human_review_dispatch.get("dispatch") or {}).get("status")),
            "genius_human_review_trend_status": genius_human_review_trend_status,
            "genius_human_review_trend_reasons": genius_human_review_trend.get("reasons"),
            "genius_human_review_trend_dispatch_status": ((genius_human_review_trend_dispatch.get("dispatch") or {}).get("status")),
            "genius_dispatch_health_gate_status": genius_dispatch_health_status,
            "genius_dispatch_health_gate_reasons": genius_dispatch_health_gate.get("reasons"),
            "genius_dispatch_health_gate_dispatch_status": ((genius_dispatch_health_gate_dispatch.get("dispatch") or {}).get("status")),
            "blend_mode": blend.get("mode"),
            "blend_mode_source": blend.get("mode_source"),
            "blend_decision": blend.get("decision"),
            "blend_weights": blend.get("weights"),
            "anchor_policy_action": anchor_tiering.get("policy_action"),
            "anchor_decision": anchor_tiering.get("decision"),
            "anchor_tier_counts": anchor_tiering.get("tier_counts"),
            "anchor_rehearsal_status": anchor_rehearsal.get("status"),
            "anchor_rehearsal_next": anchor_rehearsal.get("recommended_next"),
            "anchor_shadow_status": anchor_shadow.get("status"),
            "anchor_shadow_next": anchor_shadow.get("recommended_next"),
            "anchor_shadow_pass_ratio": ((anchor_shadow.get("summary") or {}).get("shadow_pass_ratio")),
            "anchor_promotion_status": anchor_promotion.get("status"),
            "anchor_promotion_next": anchor_promotion.get("recommended_next"),
            "anchor_promotion_candidate_count": len(anchor_promotion.get("promotion_candidates") or []),
            "anchor_promoted_status": anchor_promoted.get("status"),
            "anchor_promoted_count": anchor_promoted.get("promoted_count"),
            "anchor_sustain_status": anchor_sustain.get("status"),
            "anchor_sustain_pass_streak": ((anchor_sustain.get("current") or {}).get("pass_streak")),
            "anchor_sustain_fail_streak": ((anchor_sustain.get("current") or {}).get("fail_streak")),
            "anchor_recovery_status": anchor_recovery.get("status"),
            "anchor_recovery_candidate_count": len(anchor_recovery.get("recovery_candidates") or []),
            "anchor_drill_pass": anchor_drill.get("pass"),
            "anchor_drill_recovery_status": ((anchor_drill.get("results") or {}).get("recovery_status")),
            "anchor_drill_policy_effective_action": ((anchor_drill.get("results") or {}).get("policy_effective_action")),
            "anchor_weekly_ab_status": ((anchor_weekly_ab.get("summary") or {}).get("status")),
            "anchor_weekly_ab_pass_rate_delta": ((anchor_weekly_ab.get("summary") or {}).get("pass_rate_delta_adopt_minus_monitor")),
            "anchor_policy_stage_drill_scenarios": len(anchor_policy_stage_drill.get("results") or []),
            "anchor_handoff_status": ((anchor_handoff.get("summary") or {}).get("packet_status")),
            "anchor_handoff_recommendation": ((anchor_handoff.get("summary") or {}).get("recommendation")),
            "anchor_handoff_promotion_lane": ((anchor_handoff.get("summary") or {}).get("promotion_lane")),
            "anchor_handoff_already_promoted": ((anchor_handoff.get("summary") or {}).get("already_promoted")),
        },
        "governance_drill": {
            "external_anchor_downgrade_recovery": {
                "status": "PASS" if bool(anchor_drill.get("pass")) else "HOLD",
                "drill_pass": bool(anchor_drill.get("pass")),
                "recovery_status": ((anchor_drill.get("results") or {}).get("recovery_status")),
                "recovery_candidate_count": ((anchor_drill.get("results") or {}).get("recovery_candidate_count")),
                "policy_effective_action": ((anchor_drill.get("results") or {}).get("policy_effective_action")),
                "source_json": str(args.anchor_drill_json).replace("\\", "/"),
            },
            "external_anchor_weekly_ab": {
                "status": ((anchor_weekly_ab.get("summary") or {}).get("status")) or "UNKNOWN",
                "window_rows": ((anchor_weekly_ab.get("summary") or {}).get("window_rows")),
                "monitor_rows": ((anchor_weekly_ab.get("summary") or {}).get("monitor_rows")),
                "adopt_rows": ((anchor_weekly_ab.get("summary") or {}).get("adopt_rows")),
                "pass_rate_delta_adopt_minus_monitor": ((anchor_weekly_ab.get("summary") or {}).get("pass_rate_delta_adopt_minus_monitor")),
                "source_json": str(args.anchor_weekly_ab_json).replace("\\", "/"),
            },
            "external_anchor_policy_stage": {
                "status": "PASS" if len(anchor_policy_stage_drill.get("results") or []) >= 3 else "HOLD",
                "strict_pass_streak_threshold": anchor_policy_stage_drill.get("strict_pass_streak_threshold"),
                "scenarios": anchor_policy_stage_drill.get("results"),
                "source_json": str(args.anchor_policy_stage_drill_json).replace("\\", "/"),
            },
            "external_anchor_handoff_packet": {
                "status": ((anchor_handoff.get("summary") or {}).get("packet_status")) or "UNKNOWN",
                "recommendation": ((anchor_handoff.get("summary") or {}).get("recommendation")),
                "promotion_lane": ((anchor_handoff.get("summary") or {}).get("promotion_lane")),
                "already_promoted": ((anchor_handoff.get("summary") or {}).get("already_promoted")),
                "source_json": str(args.anchor_handoff_json).replace("\\", "/"),
            },
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json), "status": out["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
