from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_general_prophecy_holdout_evolution_candidates_v1.py"


def test_build_holdout_evolution_candidates_smoke(tmp_path: Path):
    gate = tmp_path / "gate.json"
    health = tmp_path / "health.json"
    failure = tmp_path / "failure.json"
    out = tmp_path / "candidates.json"

    gate.write_text(
        json.dumps(
            {
                "schema": "general_prophecy_explainability_holdout_gate_v1",
                "decision": "WARN_HOLDOUT_DRIFT_RISK",
                "profile": "ops",
                "thresholds": {
                    "min_holdout_direct_rate": 0.85,
                    "min_holdout_repro_rate": 0.95,
                    "min_holdout_coverage": 0.35,
                },
                "metrics_snapshot": {
                    "holdout_direct_match_rate": 0.72,
                    "holdout_reproducible_evidence_rate": 0.9,
                    "holdout_avg_biblical_keyword_coverage": 0.3,
                },
                "checks": {
                    "min_holdout_questions_pass": True,
                    "min_holdout_direct_rate_pass": False,
                    "min_holdout_repro_rate_pass": False,
                    "min_holdout_coverage_pass": False,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    health.write_text(
        json.dumps({"alert_dispatch_result": "dry_run"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    failure.write_text(
        json.dumps({"failed_step": "check_explainability_holdout_gate"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--gate-json",
            str(gate),
            "--health-json",
            str(health),
            "--failure-json",
            str(failure),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "general_prophecy_holdout_evolution_candidates_v1"
    assert doc["mode"] == "proposal_only_no_auto_apply"
    assert doc["track_wall"]["auto_apply"] is False
    assert len(doc.get("candidates") or []) >= 1
