"""Smoke: human review queue + lane promotion gates."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "scripts" / "build_logos_candidate_edge_human_review_queue_v1.py"
GATE = ROOT / "scripts" / "check_logos_candidate_edge_promotion_gate_v1.py"
CHAIN = ROOT / "scripts" / "run_logos_candidate_edge_review_promotion_chain_v1.py"
SIGNOFF_ANN = ROOT / "docs/final/fixtures/logos_candidate_edge_promotion_signoff_ann_lite_v1.example.json"


def _ann_survivors(n: int = 2) -> dict:
    rows = []
    for i in range(n):
        rows.append(
            {
                "schema": "bible_meaning_graph_edge_candidate_v1",
                "src_node_id": f"logos::A.{i}",
                "dst_node_id": f"logos::B.{i}",
                "edge_type": "semantic_ann_lite_knn",
                "similarity_ann_lite_cosine": 0.88 + i * 0.01,
                "weight": 0.88,
                "research_only": True,
                "promotion_required": True,
                "source_track": "B",
                "relation_basis": ["ann_lite_cosine"],
            }
        )
    return {
        "schema": "logos_candidate_edge_survivors_v1",
        "lane_id": "ann_lite",
        "stats": {"survivor_count": n},
        "survivors": rows,
    }


def test_human_review_queue_orders_ann_lite_first(tmp_path: Path) -> None:
    p4 = tmp_path / "4d.json"
    pa = tmp_path / "ann.json"
    out = tmp_path / "queue.json"
    p4.write_text(
        json.dumps(
            {
                "survivors": [
                    {
                        "schema": "bible_meaning_graph_edge_candidate_v1",
                        "src_node_id": "x::1",
                        "dst_node_id": "x::2",
                        "similarity_4d_cosine": 0.997,
                        "edge_type": "semantic_4d_knn",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    pa.write_text(json.dumps(_ann_survivors(2)), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(REVIEW),
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
    assert doc["schema"] == "logos_candidate_edge_human_review_queue_v1"
    assert doc["stats"]["total_items"] == 3
    assert doc["items"][0]["lane_id"] == "ann_lite"
    assert doc["items"][0]["priority"] == "primary"


def test_ann_lite_gate_lane_preset_holds_without_signoff(tmp_path: Path) -> None:
    fixture = ROOT / "docs/final/fixtures/logos_candidate_edge_promotion_signoff_ann_lite_v1.example.json"
    if not fixture.is_file():
        return
    out = tmp_path / "gate.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--lane-id",
            "ann_lite",
            "--signoff-json",
            str(fixture),
            "--output-json",
            str(out),
            "--strict",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["lane_id"] == "ann_lite"
    assert doc["gate_pass"] is False


def test_review_promotion_chain_smoke(tmp_path: Path) -> None:
    surv_ann = ROOT / "docs/final/artifacts/logos_candidate_edge_survivors_ann_lite_v1_latest.json"
    surv_4d = ROOT / "docs/final/artifacts/logos_candidate_edge_survivors_v1_latest.json"
    if not surv_ann.is_file() or not surv_4d.is_file():
        return
    chain_out = tmp_path / "chain.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(CHAIN),
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
    assert doc["schema"] == "logos_candidate_edge_review_promotion_chain_v1"
    assert doc["gates_summary"]["ann_lite"]["status"] in ("HOLD", "PASS")
    assert isinstance(doc["gates_summary"]["ann_lite"].get("gate_pass"), bool)
