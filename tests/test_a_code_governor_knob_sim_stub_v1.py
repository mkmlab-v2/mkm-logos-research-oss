"""RQ-028 A-code S2-Governor knob sim stub tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_a_code_governor_knob_sim_stub_v1.py"
MATRIX = ROOT / "experiments/a_code_12ai_v2/specs/a_code_12ai_matrix_v2.example.json"
PROFILE = ROOT / "docs/final/artifacts/commander_profile_v1.example.json"
SESSION_PANEL = ROOT / "reports/btrack_session_myeongni_panel_202606_june_prophecy.csv"
MARKET_PSYCH = ROOT / "reports/btrack_per_date_directions_market_psych_v2.json"

FORBIDDEN_KEYS = (
    "price_directional_hit_rate",
    "jaccard",
    "saving_pct",
    "live_trading",
)


def test_governor_knob_sim_runs_for_june_session_date(tmp_path: Path) -> None:
    if not SESSION_PANEL.is_file():
        pytest.skip("june session panel CSV not on disk")
    out = tmp_path / "governor_sim.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--matrix",
            str(MATRIX),
            "--profile",
            str(PROFILE),
            "--session-panel",
            str(SESSION_PANEL),
            "--session-date",
            "2026-06-05",
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
    assert report.get("schema") == "a_code_governor_knob_sim_report_v1"
    assert report.get("rq_id") == "RQ-028"
    assert report.get("cell_id") == "S2-Governor"
    assert report.get("research_only") is True
    assert report.get("session_pillars", {}).get("day") == "경술"
    knobs = report.get("adjusted_knobs") or {}
    assert 0.1 <= float(knobs.get("token_budget_lambda", 0)) <= 0.5
    assert 1 <= int(knobs.get("parallel_cap", 0)) <= 4
    delta = report.get("governor_knob_delta") or {}
    assert "token_budget_lambda_delta" in delta
    assert report.get("eval_axes", {}).get("orchestration_consistency") is True
    blob = json.dumps(report)
    for key in FORBIDDEN_KEYS:
        assert key not in blob


def test_governor_knob_sim_optional_market_psych(tmp_path: Path) -> None:
    if not SESSION_PANEL.is_file() or not MARKET_PSYCH.is_file():
        pytest.skip("session panel or market psych not on disk")
    out = tmp_path / "governor_sim_mp.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--session-date",
            "2026-06-05",
            "--market-psych",
            str(MARKET_PSYCH),
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
    drivers = report.get("drivers") or {}
    assert drivers.get("transition_hint") in {
        "aggravating",
        "recovering",
        "stable_transition",
        None,
    }
