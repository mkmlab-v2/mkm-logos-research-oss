from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_agct_sasang_size_overlay_candidate_v1.py"


def test_build_overlay_candidate_from_readiness_and_sweep(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.json"
    readiness.write_text(
        json.dumps(
            {
                "schema": "bio_dna_promotion_readiness_v1",
                "summary": {"promotion_candidate_ready": True},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    sweep = tmp_path / "sweep.json"
    sweep.write_text(
        json.dumps(
            {
                "schema": "agct_sasang_hypothesis_sweep_v1",
                "summary": {
                    "best_accuracy": 0.75,
                    "best_accuracy_permutation_p_value": 0.04,
                },
                "top_hypotheses": [
                    {
                        "mapping": {"A": "TY", "C": "SY", "G": "TE", "T": "SE"},
                        "risk_overlay": {"pearson_corr": 0.30},
                    }
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "overlay.json"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--readiness-json",
            str(readiness),
            "--sweep-json",
            str(sweep),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema"] == "agct_sasang_size_overlay_candidate_v1"
    assert data["gates"]["candidate_ready_for_human_review"] is True
    ov = data["overlay_candidate"]
    assert ov["high_risk_multiplier"] <= ov["neutral_multiplier"] <= ov["low_risk_multiplier"]
