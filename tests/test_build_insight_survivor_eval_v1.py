"""Smoke: build_insight_survivor_eval_v1 CLI writes eval JSON."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_insight_survivor_eval_v1.py"


def test_build_insight_survivor_eval_cli_smoke(tmp_path: Path) -> None:
    ins = tmp_path / "insight.json"
    out = tmp_path / "eval.json"
    doc = {
        "schema": "bible_meaning_insight_candidates_v1",
        "candidates": [
            {
                "candidate_id": "cand_001",
                "source_node_id": "aramaic::Dan.2.4",
                "hub_score": 0.4,
                "path_score": 0.5,
                "cluster_size": 3,
                "regime_tag": "imperial",
            }
        ],
    }
    ins.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--insight-json", str(ins), "--output-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    ev = json.loads(out.read_text(encoding="utf-8"))
    assert ev.get("schema") == "insight_survivor_eval_v1"
    assert len(ev.get("rows") or []) == 1
