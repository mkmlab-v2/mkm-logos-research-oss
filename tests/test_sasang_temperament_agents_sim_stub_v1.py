"""RQ-026 temperament 4-agent sim stub — schema, eval-axis separation, forbidden keys."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "experiments/sasang_temperament_agents_v1/specs/temperament_agent_state_v1.example.json"
SCHEMA = ROOT / "experiments/sasang_temperament_agents_v1/specs/temperament_agent_state_v1.schema.json"
SCRIPT = ROOT / "scripts/run_sasang_temperament_agents_sim_stub_v1.py"
MARKET_PSYCH = ROOT / "reports/btrack_per_date_directions_market_psych_v2.json"

FORBIDDEN_EVAL_KEYS = (
    "price_directional_hit_rate",
    "jaccard",
    "saving_pct",
    "predicted_direction",
    "actual_direction",
)


def test_temperament_agent_state_example_validates_against_schema() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    doc = json.loads(SPEC.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
    assert doc.get("rq_id") == "RQ-026"
    assert len(doc.get("agents") or []) == 4


def test_sim_stub_runs_and_separates_eval_axes(tmp_path: Path) -> None:
    if not MARKET_PSYCH.is_file():
        pytest.skip("market psych v2 per-date JSON not on disk")
    out = tmp_path / "sim_report.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--spec",
            str(SPEC),
            "--input",
            str(MARKET_PSYCH),
            "--out",
            str(out),
            "--max-days",
            "12",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report.get("schema") == "sasang_temperament_agents_sim_report_v1"
    assert report.get("research_only") is True
    assert report.get("not_promoted_track_a") is True
    inputs = report.get("inputs") or {}
    assert inputs.get("pathology_matrix_coupled") is True

    eval_axes = report.get("eval_axes") or {}
    assert "temperament_consistency" in eval_axes
    assert "pathology_transition_replay" in eval_axes
    for bad in FORBIDDEN_EVAL_KEYS:
        assert bad not in json.dumps(eval_axes)

    blob = json.dumps(report)
    for bad in FORBIDDEN_EVAL_KEYS:
        assert bad not in blob

    assert len(report.get("daily_steps") or []) == 12
    assert "consensus_log" in report
