from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_general_prophecy_holdout_evolution_ablation_v1.py"


def test_holdout_evolution_ablation_smoke(tmp_path: Path):
    gate = tmp_path / "gate.json"
    cands = tmp_path / "cands.json"
    out = tmp_path / "out.json"
    gate.write_text(
        json.dumps(
            {
                "schema": "general_prophecy_explainability_holdout_gate_v1",
                "thresholds": {
                    "min_holdout_direct_rate": 0.85,
                    "min_holdout_repro_rate": 0.95,
                    "min_holdout_coverage": 0.35,
                },
                "metrics_snapshot": {
                    "holdout_n_questions": 3,
                    "holdout_direct_match_rate": 0.8,
                    "holdout_reproducible_evidence_rate": 0.96,
                    "holdout_avg_biblical_keyword_coverage": 0.36,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    cands.write_text(
        json.dumps(
            {
                "schema": "general_prophecy_holdout_evolution_candidates_v1",
                "candidates": [
                    {
                        "id": "adj_direct",
                        "target": "holdout_gate.thresholds.min_holdout_direct_rate",
                        "proposed_value": 0.79,
                        "risk_level": "low",
                        "reason": "test",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    cp = subprocess.run(
        [sys.executable, str(SCRIPT), "--gate-json", str(gate), "--candidates-json", str(cands), "--output-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "general_prophecy_holdout_evolution_ablation_v1"
    assert doc["recommended_candidate_id"] == "adj_direct"
    assert doc["track_wall"]["auto_apply"] is False
