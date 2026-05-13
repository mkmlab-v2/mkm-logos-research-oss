"""Smoke: report_aramaic_semantic_edge_quality_v1 CLI aggregates edges into quality JSON."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "report_aramaic_semantic_edge_quality_v1.py"


def _edge() -> dict:
    return {
        "schema": "aramaic_graph_edge_v1",
        "src_node_id": "aramaic::Dan.2.4",
        "dst_node_id": "aramaic::Dan.2.5",
        "edge_type": "timeline_anchor",
        "weight": 0.72,
        "confidence": 0.78,
        "evidence": "stub",
        "as_of_utc": "2020-01-01T00:00:00Z",
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "semantic_overlap": 0.35,
        "shared_token_count": 2,
        "relation_basis": ["token_overlap"],
    }


def test_report_aramaic_semantic_edge_quality_cli_smoke(tmp_path: Path) -> None:
    edges = tmp_path / "edges.jsonl"
    out = tmp_path / "quality.json"
    edges.write_text(json.dumps(_edge(), ensure_ascii=False) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--edges-jsonl",
            str(edges),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "aramaic_semantic_edge_quality_v1"
    assert doc.get("edge_count") == 1
    assert "semantic_overlap_mean" in doc
    assert "edge_type_histogram" in doc
    assert doc.get("research_only") is True
    assert doc.get("source_track") == "B"
