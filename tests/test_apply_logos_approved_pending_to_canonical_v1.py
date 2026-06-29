"""Smoke: apply approved pending edges to canonical with dedupe."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPLY = ROOT / "scripts" / "apply_logos_approved_pending_to_canonical_v1.py"


def test_apply_refused_without_ack(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, str(APPLY), "--output-json", str(tmp_path / "out.json")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 3


def test_apply_dedupes_and_appends(tmp_path: Path) -> None:
    canonical = tmp_path / "edges.jsonl"
    canonical.write_text(
        json.dumps(
            {
                "schema": "bible_meaning_graph_edge_v1",
                "src_node_id": "a::1",
                "dst_node_id": "a::2",
                "edge_type": "theme_association",
                "weight": 0.5,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    pending = tmp_path / "pending.jsonl"
    pending.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "schema": "bible_meaning_graph_edge_candidate_v1",
                        "src_node_id": "a::1",
                        "dst_node_id": "a::2",
                        "weight": 0.9,
                        "edge_type": "semantic_ann_lite_knn",
                    }
                ),
                json.dumps(
                    {
                        "schema": "bible_meaning_graph_edge_candidate_v1",
                        "src_node_id": "a::3",
                        "dst_node_id": "a::4",
                        "weight": 0.88,
                        "edge_type": "semantic_ann_lite_knn",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "report.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(APPLY),
            "--canonical-edges-jsonl",
            str(canonical),
            "--pending-jsonl",
            str(pending),
            "--output-json",
            str(out),
            "--acknowledge-canonical-risk",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["appended_count"] == 1
    assert doc["skipped_duplicate"] == 1
    lines = [l for l in canonical.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2
