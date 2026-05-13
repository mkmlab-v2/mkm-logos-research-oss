"""Smoke: select_insight_survivor_candidates_v1 CLI ranks survivors from eval JSON."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "select_insight_survivor_candidates_v1.py"


def test_select_insight_survivor_candidates_cli_smoke(tmp_path: Path) -> None:
    evp = tmp_path / "eval.json"
    out = tmp_path / "survivors.json"
    ev = {
        "schema": "insight_survivor_eval_v1",
        "rows": [
            {
                "candidate_id": "cand_001",
                "fusion_candidate_score": 0.72,
                "drawdown_avoidance_score": 0.6,
                "false_positive_cost": 0.2,
                "walkforward_repro_score": 0.5,
            }
        ],
    }
    evp.write_text(json.dumps(ev, ensure_ascii=False, indent=2), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--eval-json",
            str(evp),
            "--output-json",
            str(out),
            "--top-n",
            "3",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "insight_survivor_candidates_v1"
    assert (doc.get("survivor_count") or 0) >= 1
