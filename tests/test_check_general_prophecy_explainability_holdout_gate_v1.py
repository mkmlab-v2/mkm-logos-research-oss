from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_general_prophecy_explainability_holdout_gate_v1.py"


def test_holdout_gate_smoke(tmp_path: Path):
    holdout = tmp_path / "holdout.json"
    gate = tmp_path / "gate.json"
    holdout.write_text(
        json.dumps(
            {
                "schema": "general_prophecy_explainability_holdout_report_v1",
                "holdout_core": {
                    "n_questions": 5,
                    "direct_match_rate": 0.8,
                    "reproducible_evidence_rate": 1.0,
                    "avg_biblical_keyword_coverage": 0.32,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--holdout-json",
            str(holdout),
            "--output-json",
            str(gate),
            "--min-holdout-direct-rate",
            "0.7",
            "--min-holdout-repro-rate",
            "0.9",
            "--min-holdout-coverage",
            "0.3",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(gate.read_text(encoding="utf-8"))
    assert doc["schema"] == "general_prophecy_explainability_holdout_gate_v1"
    assert doc["all_pass"] is True
    assert doc["decision"] == "GO_HOLDOUT_STABLE"


def test_holdout_gate_strict_fail_exit_2(tmp_path: Path):
    holdout = tmp_path / "holdout_fail.json"
    gate = tmp_path / "gate_fail.json"
    holdout.write_text(
        json.dumps(
            {
                "schema": "general_prophecy_explainability_holdout_report_v1",
                "holdout_core": {
                    "n_questions": 5,
                    "direct_match_rate": 0.6,
                    "reproducible_evidence_rate": 0.8,
                    "avg_biblical_keyword_coverage": 0.2,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--holdout-json",
            str(holdout),
            "--output-json",
            str(gate),
            "--profile",
            "ops",
            "--strict-exit",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 2, cp.stderr + cp.stdout
    doc = json.loads(gate.read_text(encoding="utf-8"))
    assert doc["schema"] == "general_prophecy_explainability_holdout_gate_v1"
    assert doc["all_pass"] is False
    assert doc["decision"] == "WARN_HOLDOUT_DRIFT_RISK"
