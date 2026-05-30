"""Smoke: quality report + survivor prune for candidate edges."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "scripts" / "report_logos_candidate_edges_quality_v1.py"
SELECT = ROOT / "scripts" / "select_logos_candidate_edge_survivors_v1.py"
CHAIN = ROOT / "scripts" / "run_logos_candidate_edges_offline_knn_chain_v1.py"


def _sample_edge(sim: float, src: str, dst: str) -> dict:
    return {
        "schema": "bible_meaning_graph_edge_candidate_v1",
        "src_node_id": src,
        "dst_node_id": dst,
        "edge_type": "semantic_4d_knn",
        "edge_status": "candidate",
        "weight": sim,
        "similarity_4d_cosine": sim,
        "as_of_utc": "2026-05-30T00:00:00Z",
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "relation_basis": ["offline_4d_knn"],
        "source": "build_logos_candidate_edges_offline_knn_v1",
    }


def test_quality_report_smoke(tmp_path: Path) -> None:
    edges = tmp_path / "edges.jsonl"
    out = tmp_path / "quality.json"
    rows = [
        _sample_edge(0.9999, "aramaic::A", "aramaic::B"),
        _sample_edge(0.995, "aramaic::C", "aramaic::D"),
        _sample_edge(0.93, "aramaic::E", "aramaic::F"),
    ]
    edges.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(REPORT), "--edges-jsonl", str(edges), "--output-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_candidate_edges_quality_v1"
    assert doc["edge_count"] == 3
    assert doc["saturation_warning"] is True


def test_select_survivors_respects_max_cosine(tmp_path: Path) -> None:
    edges = tmp_path / "edges.jsonl"
    out = tmp_path / "survivors.json"
    rows = [
        _sample_edge(0.9999, "aramaic::A", "aramaic::B"),
        _sample_edge(0.997, "aramaic::A", "aramaic::C"),
        _sample_edge(0.95, "aramaic::D", "aramaic::E"),
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
            "10",
            "--max-cosine",
            "0.998",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_candidate_edge_survivors_v1"
    assert doc["merge_to_canonical_allowed"] is False
    sims = [s["similarity_4d_cosine"] for s in doc["survivors"]]
    assert all(s <= 0.998 for s in sims)
    assert 0.997 in sims or 0.95 in sims


def test_chain_skip_build_when_staging_exists(tmp_path: Path) -> None:
    cand = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_candidate_v1.jsonl"
    if not cand.is_file():
        return
    chain_out = tmp_path / "chain.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(CHAIN),
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
    assert doc["schema"] == "logos_candidate_edges_offline_knn_chain_v1"
    assert doc["exit_code"] == 0
    assert len(doc["steps"]) == 3
