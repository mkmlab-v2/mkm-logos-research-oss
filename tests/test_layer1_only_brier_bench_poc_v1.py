from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "layer1_only_brier_bench_poc_v1.py"
COHORT = ROOT / "docs" / "final" / "artifacts" / "layer1_only_brier_bench_poc_v1_latest.json"
FIXTURE = ROOT / "tests" / "fixtures" / "layer1_only_brier_bench_poc_resolved_smoke_v1.json"


def test_cohort_track_wall() -> None:
    doc = json.loads(COHORT.read_text(encoding="utf-8"))
    meta = doc["poc_meta"]
    assert meta["track"] == "B"
    assert meta["track_wall"] == "B"
    assert meta["auto_bridge_to_a"] is False
    assert len(doc["forecasts"]) == 5
    assert all(f["status"] == "pending" for f in doc["forecasts"])
    assert all(f["model_source_kind"].startswith("mechanical") for f in doc["forecasts"])


def test_holdout_only_default_run(tmp_path: Path) -> None:
    out = tmp_path / "report.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--cohort", str(COHORT), "--output", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["evaluation_summary"]["status"] == "holdout_only"
    assert report["evaluation_summary"]["evaluated_n"] == 0
    assert report["evaluation_summary"]["pending_n"] == 5


def test_resolved_fixture_brier_math(tmp_path: Path) -> None:
    out = tmp_path / "report.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--cohort", str(FIXTURE), "--output", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(out.read_text(encoding="utf-8"))
    summary = report["evaluation_summary"]
    assert summary["evaluated_n"] == 5
    assert summary["brier_scores"]["uniform_baseline_score"] == 0.25
    assert "skill_vs_uniform_0_5" in summary["skill_scores_uplift"]


def test_simulation_flag_is_hypo_only(tmp_path: Path) -> None:
    out = tmp_path / "report.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--cohort",
            str(COHORT),
            "--output",
            str(out),
            "--allow-simulation",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["evaluation_summary"]["eval_mode"] == "simulation_validated_hypo"
