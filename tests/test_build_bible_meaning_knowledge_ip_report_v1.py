# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.7, K:0.3, M:0.6}
# Balance: 87
# Purpose: Ensure knowledge IP report carries explicit survivor identifiers.
# Keywords: pytest, knowledge-ip, survivor_ids, report
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_bible_meaning_knowledge_ip_report_v1.py"


def _write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_report_contains_explicit_survivor_ids(tmp_path: Path) -> None:
    insight = tmp_path / "insight.json"
    survivor = tmp_path / "survivor.json"
    report = tmp_path / "report.json"
    viz = tmp_path / "viz.json"

    _write_json(insight, {"candidates": [{"candidate_id": "cand_001"}, {"candidate_id": "cand_002"}]})
    _write_json(
        survivor,
        {
            "survivors": [
                {"candidate_id": "cand_001", "source_node_id": "x", "fusion_candidate_score": 0.7},
                {"candidate_id": "cand_002", "source_node_id": "y", "fusion_candidate_score": 0.6},
            ]
        },
    )

    proc = subprocess.run(
        [
            "py",
            str(SCRIPT),
            "--insight-json",
            str(insight),
            "--survivor-json",
            str(survivor),
            "--report-json",
            str(report),
            "--viz-json",
            str(viz),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    doc = json.loads(report.read_text(encoding="utf-8-sig"))
    assert doc.get("summary", {}).get("survivor_count") == 2
    assert doc.get("survivor_ids") == ["cand_001", "cand_002"]
    assert len(doc.get("survivors") or []) == 2

