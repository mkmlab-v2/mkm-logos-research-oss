"""Smoke: build_bible_meaning_graph_v1 CLI merges verse/bridge stubs into meaning graph JSONL."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_bible_meaning_graph_v1.py"


def _verse_node() -> dict:
    return {
        "schema": "aramaic_graph_node_v1",
        "node_id": "aramaic::Dan.2.4",
        "corpus": "aramaic",
        "ref": "Dan.2.4",
        "text_norm": "alpha beta",
        "time_bucket": "ancient_empire_cycle",
        "theme_tags": ["exile"],
        "regime_tags": ["imperial"],
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
    }


def test_build_bible_meaning_graph_cli_smoke(tmp_path: Path) -> None:
    vn = tmp_path / "verse_nodes.jsonl"
    bn = tmp_path / "bridge_nodes.jsonl"
    ve = tmp_path / "verse_edges.jsonl"
    be = tmp_path / "bridge_edges.jsonl"
    on = tmp_path / "out_nodes.jsonl"
    oe = tmp_path / "out_edges.jsonl"
    vn.write_text(json.dumps(_verse_node(), ensure_ascii=False) + "\n", encoding="utf-8")
    for p in (bn, ve, be):
        p.write_text("", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--verse-nodes-jsonl",
            str(vn),
            "--bridge-nodes-jsonl",
            str(bn),
            "--verse-edges-jsonl",
            str(ve),
            "--bridge-edges-jsonl",
            str(be),
            "--output-nodes-jsonl",
            str(on),
            "--output-edges-jsonl",
            str(oe),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    nlines = [ln for ln in on.read_text(encoding="utf-8").splitlines() if ln.strip()]
    elines = [ln for ln in oe.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(nlines) >= 3  # verse + theme + regime
    assert len(elines) >= 2
    kinds = {json.loads(ln).get("kind") for ln in nlines if json.loads(ln).get("schema") == "bible_meaning_graph_node_v1"}
    assert "theme" in kinds and "regime" in kinds
