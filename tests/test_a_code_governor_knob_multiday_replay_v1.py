"""RQ-028 multi-day governor knob replay + pathology ablation tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_a_code_governor_knob_multiday_replay_v1.py"
SESSION_PANEL = ROOT / "reports/btrack_session_myeongni_panel_202606_june_prophecy.csv"
MARKET_PSYCH = ROOT / "reports/btrack_per_date_directions_market_psych_v2.json"


def test_multiday_replay_builder_exit_zero(tmp_path: Path) -> None:
    if not SESSION_PANEL.is_file():
        pytest.skip("june session panel CSV not on disk")
    out = tmp_path / "multiday_replay.json"
    cmd = [
        sys.executable,
        str(BUILDER),
        "--session-panel",
        str(SESSION_PANEL),
        "--out",
        str(out),
    ]
    if MARKET_PSYCH.is_file():
        cmd.extend(["--market-psych", str(MARKET_PSYCH)])
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report.get("schema") == "a_code_governor_knob_multiday_replay_v1"
    assert report.get("rq_id") == "RQ-028"
    assert report.get("research_only") is True
    assert report.get("n_session_days", 0) >= 5
    assert len(report.get("holdout_dates") or []) >= 1
    consistency = report.get("eval_axes", {}).get("orchestration_consistency") or {}
    assert consistency.get("holdout") == 1.0
    series = (report.get("time_series") or {}).get("pathology_v1_2_on") or []
    assert len(series) == report["n_session_days"]
    for row in series:
        knobs = row.get("adjusted_knobs") or {}
        assert 0.1 <= float(knobs.get("token_budget_lambda", 0)) <= 0.5
        assert 1 <= int(knobs.get("parallel_cap", 0)) <= 4
    blob = json.dumps(report)
    assert "price_directional_hit_rate" not in blob
    assert "live_trading" not in blob


def test_pathology_ablation_produces_finite_delta(tmp_path: Path) -> None:
    if not SESSION_PANEL.is_file():
        pytest.skip("june session panel CSV not on disk")
    out = tmp_path / "multiday_ablation.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--session-panel",
            str(SESSION_PANEL),
            "--holdout-fraction",
            "0.15",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads(out.read_text(encoding="utf-8"))
    ablation = report.get("ablation_summary") or {}
    assert "pathology_on_vs_off_mean_cap_delta" in ablation
    assert "pathology_v1_2_vs_v1_1_mean_cap_delta" in ablation
