from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_logos_graph_expand_batch_v1.py"


def test_graph_expand_batch_monotonic(tmp_path: Path) -> None:
    nodes = tmp_path / "nodes.jsonl"
    edges = tmp_path / "edges.jsonl"
    canon = tmp_path / "canon.jsonl"
    nodes.write_text(
        json.dumps(
            {
                "schema": "aramaic_graph_node_v1",
                "node_id": "aramaic::Gen.1.1",
                "corpus": "aramaic",
                "ref": "Gen.1.1",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    edges.write_text(
        json.dumps(
            {
                "schema": "bible_meaning_graph_edge_v1",
                "src_node_id": "aramaic::Gen.1.2",
                "dst_node_id": "aramaic::Gen.1.1",
                "edge_type": "theme_association",
                "weight": 0.5,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    with canon.open("w", encoding="utf-8") as fh:
        for vid in ("Gen.1.2", "Gen.1.3", "Gen.1.4"):
            fh.write(json.dumps({"verse_id": vid, "text": "x"}, ensure_ascii=False) + "\n")

    out = tmp_path / "report.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--nodes-jsonl",
            str(nodes),
            "--edges-jsonl",
            str(edges),
            "--canon-jsonl",
            str(canon),
            "--batch-size",
            "3",
            "--skip-bundle-refresh",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["schema"] == "logos_graph_expand_batch_v1"
    assert report["counts"]["nodes_after"] >= report["counts"]["nodes_before"]
    assert report["monotonic"]["nodes_line_count_ok"] is True
    assert report["counts"]["nodes_appended"] >= 1
