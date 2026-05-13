"""Smoke: extract_bible_meaning_insight_candidates_v1 CLI writes candidates JSON."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "extract_bible_meaning_insight_candidates_v1.py"


def test_extract_bible_meaning_insight_candidates_cli_smoke(tmp_path: Path) -> None:
    nodes = tmp_path / "nodes.jsonl"
    edges = tmp_path / "edges.jsonl"
    out = tmp_path / "candidates.json"
    n = {
        "node_id": "aramaic::Dan.2.4",
        "regime_tags": ["imperial"],
    }
    e = {
        "src_node_id": "aramaic::Dan.2.4",
        "dst_node_id": "aramaic::Dan.2.5",
    }
    nodes.write_text(json.dumps(n, ensure_ascii=False) + "\n", encoding="utf-8")
    edges.write_text(json.dumps(e, ensure_ascii=False) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--nodes-jsonl",
            str(nodes),
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
    assert doc.get("schema") == "bible_meaning_insight_candidates_v1"
    assert isinstance(doc.get("candidates"), list)
