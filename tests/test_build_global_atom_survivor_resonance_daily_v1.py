# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.7, K:0.3, M:0.6}
# Balance: 87
# Purpose: Smoke contract for survivor resonance daily JSONL builder.
# Keywords: pytest, jsonl, survivor, resonance, sidecar
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_global_atom_survivor_resonance_daily_v1.py"


def _write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_build_survivor_resonance_daily_jsonl(tmp_path: Path) -> None:
    knowledge = tmp_path / "knowledge.json"
    candidates = tmp_path / "candidates.json"
    sidecar = tmp_path / "sidecar.json"
    out_jsonl = tmp_path / "resonance.jsonl"

    _write_json(knowledge, {"summary": {"survivor_count": 2}})
    _write_json(
        candidates,
        {
            "candidates": [
                {"candidate_id": "cand_001", "source_node_id": "x", "hub_score": 0.9, "path_score": 0.3, "cluster_size": 10},
                {"candidate_id": "cand_002", "source_node_id": "y", "hub_score": 0.8, "path_score": 0.2, "cluster_size": 9},
            ]
        },
    )
    _write_json(
        sidecar,
        {
            "lens_globals_for_sidecar": {"logos": {"direction_score": -0.4, "confidence": 0.5}},
            "per_date_features": [
                {
                    "eval_date": "2020-01-01",
                    "instrument": "kospi",
                    "score_row_context": {"flow_score_for_reversal": 1200.0},
                    "myeongni_insight_lines_cumulative_through_eval_date": 3,
                }
            ],
        },
    )

    proc = subprocess.run(
        [
            "py",
            str(SCRIPT),
            "--knowledge-report-json",
            str(knowledge),
            "--candidates-json",
            str(candidates),
            "--sidecar-json",
            str(sidecar),
            "--output-jsonl",
            str(out_jsonl),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    lines = [ln for ln in out_jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2
    row = json.loads(lines[0])
    assert row["schema"] == "global_atom_survivor_resonance_daily_row_v1"
    assert row["candidate_id"] in {"cand_001", "cand_002"}
    assert 0.0 <= float(row["resonance_score"]) <= 1.0

