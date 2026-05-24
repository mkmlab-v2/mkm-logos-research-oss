from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRAPH = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_meaning_topology_graph_slice_v1.json"
)


def test_seed_chain_smoke(tmp_path: Path) -> None:
    out = tmp_path / "seed_chain.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_logos_graph_seed_chain_v1.py"),
            "--graph-json",
            str(GRAPH.relative_to(ROOT)),
            "--out-json",
            str(out),
            "--seed-count",
            "4",
            "--max-verses",
            "12",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_graph_seed_chain_v1"
    verses = doc["graph_rag"]["verse_node_ids"]
    assert len(verses) >= 1
    assert all("::" in v for v in verses)
