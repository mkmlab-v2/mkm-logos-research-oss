from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_graphrag_pilot_router_v1.py"


def _write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8",
    )


def test_graphrag_router_smoke_with_korean_aliases_and_brief(tmp_path: Path) -> None:
    gate = tmp_path / "gate.json"
    nodes = tmp_path / "nodes.jsonl"
    edges = tmp_path / "edges.jsonl"
    out = tmp_path / "out.json"

    _write_json(
        gate,
        {
            "schema": "multi_symbol_gate_summary_v1",
            "summary": {"status": "GO"},
        },
    )
    _write_jsonl(
        nodes,
        [
            {
                "node_id": "n1",
                "assigned_symbol": "babel_tower",
                "candidate_id": "c1",
                "regime_tag": "empire_transition",
                "hub_score": 0.8,
                "path_score": 0.5,
                "cluster_size": 5,
                "atom_sequence": ["DESIRE_TRIGGER"],
            },
            {
                "node_id": "n2",
                "assigned_symbol": "exodus_return",
                "candidate_id": "c2",
                "regime_tag": "empire_transition",
                "hub_score": 0.7,
                "path_score": 0.4,
                "cluster_size": 4,
                "atom_sequence": ["RESTORATION_ARC"],
            },
        ],
    )
    _write_jsonl(
        edges,
        [
            {
                "source": "n1",
                "target": "n2",
                "similarity": 0.95,
                "edge_type": "topological_resonance",
                "gate_passed": True,
            }
        ],
    )

    cp = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--question",
            "바벨 출애굽",
            "--nodes-jsonl",
            str(nodes),
            "--edges-jsonl",
            str(edges),
            "--gate-json",
            str(gate),
            "--output",
            str(out),
            "--emit-answer-brief",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "graphrag_pilot_router_v1"
    assert doc["observation_only"] is True
    assert "babel_tower" in doc["seed_keywords"]
    assert "exodus_return" in doc["seed_keywords"]
    assert len(doc["selected_nodes"]) >= 1
    assert doc["answer_brief"]["mode"] == "OBSERVATION_ONLY"


def test_graphrag_router_blocks_when_gate_not_go(tmp_path: Path) -> None:
    gate = tmp_path / "gate_hold.json"
    nodes = tmp_path / "nodes.jsonl"
    edges = tmp_path / "edges.jsonl"
    out = tmp_path / "out.json"

    _write_json(gate, {"summary": {"status": "HOLD"}})
    _write_jsonl(nodes, [{"node_id": "n1", "assigned_symbol": "babel_tower"}])
    _write_jsonl(edges, [])

    cp = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--question",
            "바벨",
            "--nodes-jsonl",
            str(nodes),
            "--edges-jsonl",
            str(edges),
            "--gate-json",
            str(gate),
            "--output",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 3
    assert not out.exists()


def test_graphrag_router_writes_empty_observation_if_no_seed(tmp_path: Path) -> None:
    gate = tmp_path / "gate_go.json"
    nodes = tmp_path / "nodes.jsonl"
    edges = tmp_path / "edges.jsonl"
    out = tmp_path / "out_empty.json"

    _write_json(gate, {"summary": {"status": "GO"}})
    _write_jsonl(nodes, [{"node_id": "n1", "assigned_symbol": "tree_of_knowledge_good_evil"}])
    _write_jsonl(edges, [])

    cp = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--question",
            "완전무관키워드",
            "--nodes-jsonl",
            str(nodes),
            "--edges-jsonl",
            str(edges),
            "--gate-json",
            str(gate),
            "--output",
            str(out),
            "--emit-answer-brief",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["seed_node_ids"] == []
    assert doc["selected_nodes"] == []
    assert "no matched seed" in doc["answer_brief"]["text"].lower()
