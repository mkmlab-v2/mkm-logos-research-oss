"""Smoke: ANN-lite lane + dual-lane compare for Logos candidate edges."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "scripts" / "report_logos_candidate_edges_quality_v1.py"
SELECT = ROOT / "scripts" / "select_logos_candidate_edge_survivors_v1.py"
COMPARE = ROOT / "scripts" / "compare_logos_candidate_edge_lanes_v1.py"
CHAIN_ANN = ROOT / "scripts" / "run_logos_candidate_edges_ann_lite_chain_v1.py"


def _ann_edge(sim: float, src: str, dst: str) -> dict:
    return {
        "schema": "bible_meaning_graph_edge_candidate_v1",
        "src_node_id": src,
        "dst_node_id": dst,
        "edge_type": "semantic_ann_lite_knn",
        "edge_status": "candidate",
        "weight": sim,
        "similarity_ann_lite_cosine": sim,
        "embedding_mode": "sentence_transformers_v1",
        "as_of_utc": "2026-05-30T00:00:00Z",
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "relation_basis": ["ann_lite_cosine"],
        "source": "build_logos_candidate_edges_from_ann_lite_v1",
    }


def test_ann_lite_quality_no_saturation_warning(tmp_path: Path) -> None:
    edges = tmp_path / "edges.jsonl"
    out = tmp_path / "quality.json"
    rows = [_ann_edge(0.88, "logos::A", "logos::B"), _ann_edge(0.91, "logos::C", "logos::D")]
    edges.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(REPORT),
            "--edges-jsonl",
            str(edges),
            "--output-json",
            str(out),
            "--lane-id",
            "ann_lite",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["lane_id"] == "ann_lite"
    assert doc["saturation_warning"] is False
    assert doc["similarity_field"] == "similarity_ann_lite_cosine"


def test_ann_lite_select_uses_ann_cosine(tmp_path: Path) -> None:
    edges = tmp_path / "edges.jsonl"
    out = tmp_path / "survivors.json"
    rows = [
        _ann_edge(0.996, "logos::A", "logos::B"),
        _ann_edge(0.92, "logos::A", "logos::C"),
    ]
    edges.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SELECT),
            "--edges-jsonl",
            str(edges),
            "--output-json",
            str(out),
            "--skip-pruned-jsonl",
            "--top-n",
            "5",
            "--max-cosine",
            "0.995",
            "--lane-id",
            "ann_lite",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["lane_id"] == "ann_lite"
    assert len(doc["survivors"]) == 1
    assert doc["survivors"][0]["similarity_ann_lite_cosine"] == 0.92


def test_lane_compare_overlap(tmp_path: Path) -> None:
    doc_4d = {
        "survivors": [
            {"src_node_id": "a::1", "dst_node_id": "a::2"},
            {"src_node_id": "a::3", "dst_node_id": "a::4"},
        ]
    }
    doc_ann = {
        "survivors": [
            {"src_node_id": "a::2", "dst_node_id": "a::1"},
            {"src_node_id": "a::5", "dst_node_id": "a::6"},
        ]
    }
    p4 = tmp_path / "4d.json"
    pa = tmp_path / "ann.json"
    out = tmp_path / "compare.json"
    p4.write_text(json.dumps(doc_4d), encoding="utf-8")
    pa.write_text(json.dumps(doc_ann), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(COMPARE),
            "--survivors-4d-json",
            str(p4),
            "--survivors-ann-json",
            str(pa),
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
    assert doc["schema"] == "logos_candidate_edge_lane_compare_v1"
    assert doc["pair_sets"]["overlap_count"] == 1
    assert doc["pair_sets"]["only_4d_count"] == 1
    assert doc["pair_sets"]["only_ann_lite_count"] == 1


def test_ann_lite_chain_skip_build_when_staging_exists(tmp_path: Path) -> None:
    cand = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_candidate_ann_lite_v1.jsonl"
    if not cand.is_file():
        return
    chain_out = tmp_path / "chain.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(CHAIN_ANN),
            "--skip-build",
            "--chain-out",
            str(chain_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(chain_out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_candidate_edges_ann_lite_chain_v1"
    assert doc["exit_code"] == 0
    assert len(doc["steps"]) == 2
