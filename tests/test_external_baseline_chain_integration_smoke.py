from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


def test_chain_level_smoke_with_synthetic_artifacts(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    start_sweep = artifacts / "start.json"
    expand_sweep = artifacts / "expand.json"
    thresholds = artifacts / "thresholds.json"
    dual = artifacts / "dual.json"
    brief = artifacts / "brief.json"
    comparison = artifacts / "comparison.json"
    index = artifacts / "index.json"
    review_queue = artifacts / "review_queue.json"
    review_resolution = artifacts / "review_resolution.json"
    extended_status = artifacts / "extended_status.json"
    recalibration_hint = artifacts / "recalibration_hint.json"
    action_history = artifacts / "action_history.json"
    threshold_tuning_proposal = artifacts / "threshold_tuning_proposal.json"
    threshold_apply_gate = artifacts / "threshold_apply_gate.json"
    threshold_apply_approval = artifacts / "threshold_apply_approval.json"
    threshold_apply_log = artifacts / "threshold_apply_log.jsonl"
    threshold_apply_log_summary = artifacts / "threshold_apply_log_summary.json"
    health_check = artifacts / "health_check.json"
    health_alert = artifacts / "health_alert.json"
    approval_expiry_warning = artifacts / "approval_expiry_warning.json"
    weekly_rollup = artifacts / "weekly_rollup.json"
    threshold_effect_report = artifacts / "threshold_effect_report.json"
    quality_gate = artifacts / "quality_gate.json"
    global_report = artifacts / "global_report.json"
    core100_report = artifacts / "core100_report.json"
    fullcanon_report = artifacts / "fullcanon_report.json"

    _write_json(
        start_sweep,
        {"rows": [{"top_k": 100, "coverage_overlap": 0.0003, "precision_at_k": 0.02, "delta_random_baseline": 0.003}]},
    )
    _write_json(
        expand_sweep,
        {"rows": [{"top_k": 100, "coverage_overlap": 0.0001, "precision_at_k": 0.04, "delta_random_baseline": 0.012}]},
    )
    _write_json(
        thresholds,
        {
            "thresholds": {
                "coverage_overlap_min_watch": 0.000257,
                "coverage_overlap_min_promising": 0.004849,
                "delta_random_baseline_min_watch": 0.0,
                "delta_random_baseline_min_promising": 0.00017,
                "precision_at_k_min_watch": 0.001,
            }
        },
    )
    _write_json(quality_gate, {"gate": {"pass": True}})
    _write_json(review_queue, {"included": True, "items": [{"id": "r1"}]})
    _write_json(review_resolution, {"resolution_state": "pending"})
    _write_json(extended_status, {"extended_sweep_status": "success"})
    _write_json(recalibration_hint, {"hint_active": False})
    _write_json(action_history, {"monitor_only_streak": 1})
    _write_json(threshold_tuning_proposal, {"proposed_thresholds": {"coverage_overlap_min_watch": 0.001}})
    _write_json(threshold_apply_gate, {"can_apply_thresholds": False})
    _write_json(threshold_apply_approval, {"approved": False})
    threshold_apply_log.write_text("", encoding="utf-8")
    _write_json(threshold_apply_log_summary, {"apply_count_total": 0})
    _write_json(health_check, {"all_healthy": True})
    _write_json(health_alert, {"active": False})
    _write_json(approval_expiry_warning, {"active": False})
    _write_json(weekly_rollup, {"summary": {"hint_active": False, "monitor_only_streak": 1, "apply_count_total": 0, "all_healthy": True}})
    _write_json(threshold_effect_report, {"label_distribution": {"promising": 0, "watch": 0, "below_watch": 3}})
    _write_json(global_report, {"counts": {"overlap_pair_count": 1, "internal_unique_pairs_normalized": 10}, "metrics": {"coverage_overlap": 0.0001, "precision_at_k": 0.01, "delta_random_baseline": 0.0}})
    _write_json(core100_report, {"counts": {"overlap_pair_count": 2, "internal_unique_pairs_normalized": 20}, "metrics": {"coverage_overlap": 0.0003, "precision_at_k": 0.03, "delta_random_baseline": 0.006}})
    _write_json(fullcanon_report, {"counts": {"overlap_pair_count": 3, "internal_unique_pairs_normalized": 30}, "metrics": {"coverage_overlap": 0.005, "precision_at_k": 0.001, "delta_random_baseline": 0.0002}})

    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "build_external_baseline_dual_mode_report_v1.py"),
            "--start-sweep-json",
            str(start_sweep),
            "--expand-sweep-json",
            str(expand_sweep),
            "--thresholds-json",
            str(thresholds),
            "--output-json",
            str(dual),
        ],
        cwd=str(ROOT),
        check=True,
    )
    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "build_external_baseline_exploration_signal_brief_v1.py"),
            "--dual-mode-json",
            str(dual),
            "--output-json",
            str(brief),
        ],
        cwd=str(ROOT),
        check=True,
    )
    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "build_external_baseline_overlap_comparison_v1.py"),
            "--report-global",
            str(global_report),
            "--report-core100",
            str(core100_report),
            "--report-fullcanon",
            str(fullcanon_report),
            "--thresholds-json",
            str(thresholds),
            "--quality-gate-json",
            str(quality_gate),
            "--dual-mode-json",
            str(dual),
            "--exploration-brief-json",
            str(brief),
            "--output-json",
            str(comparison),
        ],
        cwd=str(ROOT),
        check=True,
    )
    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "build_external_baseline_latest_index_v1.py"),
            "--comparison-json",
            str(comparison),
            "--dual-mode-json",
            str(dual),
            "--exploration-brief-json",
            str(brief),
            "--audit-json",
            str(quality_gate),
            "--human-review-queue-json",
            str(review_queue),
            "--extended-sweep-status-json",
            str(extended_status),
            "--human-review-resolution-json",
            str(review_resolution),
            "--threshold-recalibration-hint-json",
            str(recalibration_hint),
            "--action-history-json",
            str(action_history),
            "--threshold-tuning-proposal-json",
            str(threshold_tuning_proposal),
            "--threshold-apply-gate-json",
            str(threshold_apply_gate),
            "--threshold-apply-approval-json",
            str(threshold_apply_approval),
            "--threshold-apply-log-jsonl",
            str(threshold_apply_log),
            "--threshold-apply-log-summary-json",
            str(threshold_apply_log_summary),
            "--health-check-json",
            str(health_check),
            "--health-alert-json",
            str(health_alert),
            "--approval-expiry-warning-json",
            str(approval_expiry_warning),
            "--weekly-rollup-json",
            str(weekly_rollup),
            "--threshold-effect-report-json",
            str(threshold_effect_report),
            "--output-json",
            str(index),
        ],
        cwd=str(ROOT),
        check=True,
    )

    d = json.loads(dual.read_text(encoding="utf-8"))
    assert d["exploratory_mode"]["best_row_by_delta_then_precision"]["exploration_signal"] == "strong_delta"
    b = json.loads(brief.read_text(encoding="utf-8"))
    assert b["included"] is True
    c = json.loads(comparison.read_text(encoding="utf-8"))
    assert c["operating_mode_ref"] == str(dual)
    assert c["exploratory_mode_ref"] == str(brief)
    i = json.loads(index.read_text(encoding="utf-8"))
    assert i["artifacts"]["comparison"] == str(comparison)
    assert i["artifacts"]["human_review_queue"] == str(review_queue)
    assert i["artifacts"]["extended_sweep_status"] == str(extended_status)
    assert i["artifacts"]["human_review_resolution"] == str(review_resolution)
    assert i["artifacts"]["threshold_recalibration_hint"] == str(recalibration_hint)
    assert i["artifacts"]["action_history"] == str(action_history)
    assert i["artifacts"]["threshold_tuning_proposal"] == str(threshold_tuning_proposal)
    assert i["artifacts"]["threshold_apply_gate"] == str(threshold_apply_gate)
    assert i["artifacts"]["threshold_apply_approval"] == str(threshold_apply_approval)
    assert i["artifacts"]["threshold_apply_log"] == str(threshold_apply_log)
    assert i["artifacts"]["threshold_apply_log_summary"] == str(threshold_apply_log_summary)
    assert i["artifacts"]["health_check"] == str(health_check)
    assert i["artifacts"]["health_alert"] == str(health_alert)
    assert i["artifacts"]["approval_expiry_warning"] == str(approval_expiry_warning)
    assert i["artifacts"]["weekly_rollup"] == str(weekly_rollup)
    assert i["artifacts"]["threshold_effect_report"] == str(threshold_effect_report)
