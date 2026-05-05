#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.3, M:0.6}
# Balance: 90
# Purpose: Build one-file index of latest external baseline artifacts.
# Keywords: index, latest, artifacts, btrack
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def main() -> int:
    ap = argparse.ArgumentParser(description="Build latest index for external baseline artifacts.")
    ap.add_argument("--comparison-json", default="docs/final/artifacts/external_bible_crossref_overlap_comparison_latest.json")
    ap.add_argument("--dual-mode-json", default="docs/final/artifacts/external_bible_crossref_dual_mode_report_latest.json")
    ap.add_argument("--exploration-brief-json", default="docs/final/artifacts/external_bible_crossref_exploration_signal_brief_latest.json")
    ap.add_argument("--audit-json", default="docs/final/artifacts/core100_node_ref_audit_sample_latest.json")
    ap.add_argument("--extended-sweep-summary-json", default="docs/final/artifacts/external_bible_crossref_extended_sweep_summary_latest.json")
    ap.add_argument("--human-review-queue-json", default="docs/final/artifacts/external_bible_crossref_human_review_queue_latest.json")
    ap.add_argument("--human-review-resolution-json", default="docs/final/artifacts/external_bible_crossref_human_review_resolution_latest.json")
    ap.add_argument("--extended-sweep-status-json", default="docs/final/artifacts/external_bible_crossref_extended_sweep_status_latest.json")
    ap.add_argument("--threshold-recalibration-hint-json", default="docs/final/artifacts/external_bible_crossref_threshold_recalibration_hint_latest.json")
    ap.add_argument("--action-history-json", default="docs/final/artifacts/external_bible_crossref_action_history_latest.json")
    ap.add_argument("--threshold-tuning-proposal-json", default="docs/final/artifacts/btrack_external_baseline_threshold_tuning_proposal_latest.json")
    ap.add_argument("--threshold-apply-gate-json", default="docs/final/artifacts/external_bible_crossref_threshold_apply_gate_latest.json")
    ap.add_argument("--threshold-apply-approval-json", default="docs/final/artifacts/external_bible_crossref_threshold_apply_approval_latest.json")
    ap.add_argument("--threshold-apply-log-jsonl", default="docs/final/artifacts/external_bible_crossref_threshold_apply_log.jsonl")
    ap.add_argument("--threshold-apply-log-summary-json", default="docs/final/artifacts/external_bible_crossref_threshold_apply_log_summary_latest.json")
    ap.add_argument("--health-check-json", default="docs/final/artifacts/external_bible_crossref_health_check_latest.json")
    ap.add_argument("--health-alert-json", default="docs/final/artifacts/external_bible_crossref_health_alert_latest.json")
    ap.add_argument("--approval-expiry-warning-json", default="docs/final/artifacts/external_bible_crossref_approval_expiry_warning_latest.json")
    ap.add_argument("--weekly-rollup-json", default="docs/final/artifacts/external_bible_crossref_weekly_rollup_latest.json")
    ap.add_argument("--threshold-effect-report-json", default="docs/final/artifacts/external_bible_crossref_threshold_effect_report_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/external_bible_crossref_latest_index.json")
    args = ap.parse_args()

    p_comparison = resolve(args.comparison_json)
    p_dual = resolve(args.dual_mode_json)
    p_brief = resolve(args.exploration_brief_json)
    p_audit = resolve(args.audit_json)
    p_extended = resolve(args.extended_sweep_summary_json)
    p_review_queue = resolve(args.human_review_queue_json)
    p_review_resolution = resolve(args.human_review_resolution_json)
    p_extended_status = resolve(args.extended_sweep_status_json)
    p_recalibration_hint = resolve(args.threshold_recalibration_hint_json)
    p_action_history = resolve(args.action_history_json)
    p_threshold_tuning_proposal = resolve(args.threshold_tuning_proposal_json)
    p_threshold_apply_gate = resolve(args.threshold_apply_gate_json)
    p_threshold_apply_approval = resolve(args.threshold_apply_approval_json)
    p_threshold_apply_log = resolve(args.threshold_apply_log_jsonl)
    p_threshold_apply_log_summary = resolve(args.threshold_apply_log_summary_json)
    p_health_check = resolve(args.health_check_json)
    p_health_alert = resolve(args.health_alert_json)
    p_approval_expiry_warning = resolve(args.approval_expiry_warning_json)
    p_weekly_rollup = resolve(args.weekly_rollup_json)
    p_threshold_effect_report = resolve(args.threshold_effect_report_json)
    out_path = resolve(args.output_json)

    out = {
        "schema": "external_bible_crossref_latest_index_v1",
        "generated_at_utc": now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "artifacts": {
            "comparison": str(p_comparison) if p_comparison.is_file() else None,
            "dual_mode": str(p_dual) if p_dual.is_file() else None,
            "exploration_brief": str(p_brief) if p_brief.is_file() else None,
            "audit_sample": str(p_audit) if p_audit.is_file() else None,
            "extended_sweep_summary": str(p_extended) if p_extended.is_file() else None,
            "human_review_queue": str(p_review_queue) if p_review_queue.is_file() else None,
            "human_review_resolution": str(p_review_resolution) if p_review_resolution.is_file() else None,
            "extended_sweep_status": str(p_extended_status) if p_extended_status.is_file() else None,
            "threshold_recalibration_hint": str(p_recalibration_hint) if p_recalibration_hint.is_file() else None,
            "action_history": str(p_action_history) if p_action_history.is_file() else None,
            "threshold_tuning_proposal": str(p_threshold_tuning_proposal) if p_threshold_tuning_proposal.is_file() else None,
            "threshold_apply_gate": str(p_threshold_apply_gate) if p_threshold_apply_gate.is_file() else None,
            "threshold_apply_approval": str(p_threshold_apply_approval) if p_threshold_apply_approval.is_file() else None,
            "threshold_apply_log": str(p_threshold_apply_log) if p_threshold_apply_log.is_file() else None,
            "threshold_apply_log_summary": str(p_threshold_apply_log_summary) if p_threshold_apply_log_summary.is_file() else None,
            "health_check": str(p_health_check) if p_health_check.is_file() else None,
            "health_alert": str(p_health_alert) if p_health_alert.is_file() else None,
            "approval_expiry_warning": str(p_approval_expiry_warning) if p_approval_expiry_warning.is_file() else None,
            "weekly_rollup": str(p_weekly_rollup) if p_weekly_rollup.is_file() else None,
            "threshold_effect_report": str(p_threshold_effect_report) if p_threshold_effect_report.is_file() else None,
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
