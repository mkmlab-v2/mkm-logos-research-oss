"""Headline gates recommended chain + allowlist gate on deadzone sweep."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def test_headline_gate_params_in_allowlist() -> None:
    from evolution_auto_apply_allowlist_v1 import assert_headline_gate_sweep_allowed

    assert_headline_gate_sweep_allowed(min_confidence=0.18, score_abs_deadzone=0.0)


def test_deadzone_sweep_rejects_out_of_range_grid() -> None:
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "sweep_prophecy_headline_deadzone_hold_v1.py"),
            "--score-json",
            str(ROOT / "reports" / "btrack_prophecy_score_recommended_eval_chain_v1_latest.json"),
            "--per-date-json",
            str(ROOT / "reports" / "btrack_ensemble_per_date_directions_180d_v1_latest.json"),
            "--min-confidence-grid",
            "1.5",
            "--score-abs-deadzone-grid",
            "0.0",
            "--output",
            str(ROOT / "reports" / "tmp_headline_sweep_allowlist_fail.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode != 0
    assert "allowlist" in (cp.stderr + cp.stdout).lower()


def test_headline_gates_chain_smoke_if_inputs_exist() -> None:
    score = ROOT / "reports" / "btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
    if not score.is_file():
        return
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_prophecy_btrack_headline_gates_recommended_chain_v1.py"),
            "--min-confidence-grid",
            "0.0,0.18",
            "--score-abs-deadzone-grid",
            "0.0,0.18",
            "--skip-ensemble-build",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr
    out = ROOT / "reports" / "prophecy_btrack_headline_gates_recommended_chain_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "prophecy_btrack_headline_gates_recommended_chain_v1"
    assert doc["headline_kpi_auto_apply"] is False
