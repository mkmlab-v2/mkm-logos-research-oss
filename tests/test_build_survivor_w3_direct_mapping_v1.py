# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.7, K:0.3, M:0.5}
# Balance: 86
# Purpose: Smoke test survivor-to-W3 direct mapping seed builder.
# Keywords: pytest, mapping, survivor, w3
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_survivor_w3_direct_mapping_v1.py"


def _write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_build_direct_mapping_seed(tmp_path: Path) -> None:
    knowledge = tmp_path / "knowledge.json"
    candidates = tmp_path / "candidates.json"
    w3 = tmp_path / "w3.json"
    out = tmp_path / "map.json"

    _write_json(knowledge, {"summary": {"survivor_count": 2}, "survivor_ids": ["cand_001", "cand_002"]})
    _write_json(candidates, {"candidates": [{"candidate_id": "cand_001"}, {"candidate_id": "cand_002"}]})
    _write_json(w3, {"top_n_results": [{"sample_id": "S1", "resonance_score": 0.9}, {"sample_id": "S2", "resonance_score": 0.8}]})

    proc = subprocess.run(
        [
            "py",
            str(SCRIPT),
            "--knowledge-report-json",
            str(knowledge),
            "--candidates-json",
            str(candidates),
            "--w3-result-json",
            str(w3),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "global_atom_survivor_w3_direct_mapping_v1"
    assert doc["mapping_strategy"] == "rank_aligned_topk_window_v2"
    rows = doc.get("rows") or []
    assert len(rows) == 2
    assert rows[0]["assigned_sample_ids"]


def test_build_direct_mapping_with_multiple_samples(tmp_path: Path) -> None:
    knowledge = tmp_path / "knowledge.json"
    candidates = tmp_path / "candidates.json"
    w3 = tmp_path / "w3.json"
    out = tmp_path / "map.json"

    _write_json(knowledge, {"summary": {"survivor_count": 2}, "survivor_ids": ["cand_001", "cand_002"]})
    _write_json(
        candidates,
        {
            "candidates": [
                {"candidate_id": "cand_001", "fusion_candidate_score": 0.9},
                {"candidate_id": "cand_002", "fusion_candidate_score": 0.6},
            ]
        },
    )
    _write_json(
        w3,
        {
            "top_n_results": [
                {"sample_id": "S1", "resonance_score": 0.91},
                {"sample_id": "S2", "resonance_score": 0.89},
                {"sample_id": "S3", "resonance_score": 0.6},
            ]
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
            "--w3-result-json",
            str(w3),
            "--samples-per-survivor",
            "2",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc["samples_per_survivor"] == 2
    rows = doc.get("rows") or []
    assert rows and len(rows[0]["assigned_sample_ids"]) == 2

