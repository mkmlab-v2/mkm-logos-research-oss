"""CLI smoke for apply_logos_chronology_to_graph_v1.py (tmp graph append)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_apply_chronology_overlay_and_tmp_append(tmp_path: Path) -> None:
    chrono = ROOT / "docs/final/artifacts/fixtures/logos_chronology_v1.example.json"
    nodes = tmp_path / "nodes.jsonl"
    edges = tmp_path / "edges.jsonl"
    nodes.write_text("", encoding="utf-8")
    edges.write_text("", encoding="utf-8")
    overlay = tmp_path / "overlay.json"
    report = tmp_path / "report.json"
    cmd = [
        sys.executable,
        str(ROOT / "scripts/apply_logos_chronology_to_graph_v1.py"),
        "--chronology-json",
        str(chrono),
        "--nodes-jsonl",
        str(nodes),
        "--edges-jsonl",
        str(edges),
        "--overlay-out",
        str(overlay),
        "--report-out",
        str(report),
        "--write-graph-append",
    ]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert cp.returncode == 0, cp.stderr or cp.stdout
    doc = json.loads(overlay.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_chronology_showroom_overlay_v1"
    assert len(doc.get("era_nodes") or []) >= 2
    assert nodes.read_text(encoding="utf-8").strip()
    assert edges.read_text(encoding="utf-8").strip()
