from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_run_canon_singularity_chain_dry_run():
    root = Path(__file__).resolve().parents[1]
    cmd = [
        sys.executable,
        str(root / "scripts" / "core" / "run_canon_singularity_chain_v1.py"),
        "--canon-jsonl",
        "data/logos/verse_decoded_v2.jsonl",
        "--dry-run",
    ]
    cp = subprocess.run(cmd, check=False, cwd=root, capture_output=True, text=True)
    assert cp.returncode == 0
    out = cp.stdout
    assert "build_original_corpus_regime_singularity_report_v1.py --canon-only" in out
    assert "build_original_corpus_regime_singularity_balanced_report_v1.py --canon-only" in out
    assert "build_canon_singularity_lane_summary_v1.py --input-json" in out
    assert "validate_canon_singularity_outputs_v1.py --report-json" in out
    assert "--output-json docs/final/artifacts/original_corpus_regime_singularity_canon_quality_gate_v1.json" in out
    assert "build_canon_singularity_gate_health_summary_v1.py --history-jsonl" in out
    assert "enforce_canon_singularity_gate_health_v1.py --health-summary-json" not in out
    assert "build_canon_singularity_insight_minimum_v1.py --summary-json" in out
    assert "validate_canon_singularity_insight_minimum_v1.py --input-json" in out
    assert "build_canon_singularity_insight_delta_summary_v1.py --history-jsonl" in out
    assert "--min-score-delta 0.001" in out
    assert "build_canon_singularity_insight_explainability_v1.py --insight-json" in out
    assert "validate_canon_singularity_insight_explainability_v1.py --input-json" in out
    assert "build_canon_singularity_insight_explainability_benchmark_cohort_v1.py --explainability-json" in out
    assert "validate_canon_singularity_insight_explainability_benchmark_v1.py --input-json" in out
    assert "build_canon_singularity_insight_slice_stability_v1.py --history-jsonl" in out
    assert "validate_canon_singularity_insight_slice_stability_v1.py --input-json" in out
    assert "build_canon_singularity_weekly_brief_v1.py --insight-history-jsonl" in out
    assert "validate_canon_singularity_weekly_brief_v1.py --input-json" in out
    assert "build_canon_singularity_weekly_false_alert_review_v1.py --weekly-brief-json" in out
    assert "build_canon_singularity_consistency_check_v1.py --gate-history-jsonl" in out
    assert "build_canon_singularity_promotion_gate_v1.py --health-summary-json" in out
    assert "build_canon_singularity_promotion_dashboard_v1.py --health-summary-json" in out
    assert "build_canon_singularity_promotion_alert_v1.py --promotion-gate-json" in out
    assert "build_canon_singularity_promotion_readiness_report_v1.py --promotion-history-jsonl" in out
    assert "build_canon_singularity_regime_calibration_round_v1.py --insight-delta-json" in out
    assert "build_canon_singularity_strict_baseline_freeze_v2_rollover_v1.py --freeze-v1-json" in out
    assert "build_canon_singularity_strict_baseline_freeze_v2_stability_gate_v1.py --history-jsonl" in out
    assert "build_canon_singularity_promotion_go_no_go_v1.py --promotion-gate-json" in out
    assert "build_canon_singularity_strict_baseline_freeze_vfinal_v1.py --promotion-go-no-go-json" in out
    assert "build_canon_singularity_strict_baseline_freeze_generation_diff_vfinal_v1.py --freeze-v1-json" in out


def test_run_canon_singularity_chain_dry_run_with_health_enforcement():
    root = Path(__file__).resolve().parents[1]
    cmd = [
        sys.executable,
        str(root / "scripts" / "core" / "run_canon_singularity_chain_v1.py"),
        "--canon-jsonl",
        "data/logos/verse_decoded_v2.jsonl",
        "--enforce-health",
        "--dry-run",
    ]
    cp = subprocess.run(cmd, check=False, cwd=root, capture_output=True, text=True)
    assert cp.returncode == 0
    out = cp.stdout
    assert "enforce_canon_singularity_gate_health_v1.py --health-summary-json" in out


def test_run_canon_singularity_chain_dry_run_with_promotion_enforcement():
    root = Path(__file__).resolve().parents[1]
    cmd = [
        sys.executable,
        str(root / "scripts" / "core" / "run_canon_singularity_chain_v1.py"),
        "--canon-jsonl",
        "data/logos/verse_decoded_v2.jsonl",
        "--enforce-promotion",
        "--dry-run",
    ]
    cp = subprocess.run(cmd, check=False, cwd=root, capture_output=True, text=True)
    assert cp.returncode == 0
    out = cp.stdout
    assert "build_canon_singularity_promotion_gate_v1.py --health-summary-json" in out


def test_run_canon_singularity_chain_dry_run_with_delta_governance():
    root = Path(__file__).resolve().parents[1]
    cmd = [
        sys.executable,
        str(root / "scripts" / "core" / "run_canon_singularity_chain_v1.py"),
        "--canon-jsonl",
        "data/logos/verse_decoded_v2.jsonl",
        "--auto-apply-calibration",
        "--enforce-delta-governance",
        "--dry-run",
    ]
    cp = subprocess.run(cmd, check=False, cwd=root, capture_output=True, text=True)
    assert cp.returncode == 0
    out = cp.stdout
    assert "build_canon_singularity_delta_cutoff_autotune_v1.py --calibration-json" in out
    assert "build_canon_singularity_delta_cutoff_governance_gate_v1.py --history-jsonl" in out

