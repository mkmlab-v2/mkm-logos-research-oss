"""Tests for GraphRAG router -> showroom Q&A preset export."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/export_showroom_qa_router_paths_v1.py"
GRAPH = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
PRESETS = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_meaning_topology_qa_presets_v1.json"
)


def test_export_router_paths_single_preset(tmp_path: Path) -> None:
    if not GRAPH.is_file() or not PRESETS.is_file():
        return
    out_presets = tmp_path / "presets.json"
    out_sidecar = tmp_path / "sidecar.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--graph-json",
            str(GRAPH),
            "--presets-json",
            str(PRESETS),
            "--out-presets-json",
            str(out_presets),
            "--out-sidecar-json",
            str(out_sidecar),
            "--mirror-artifact",
            str(tmp_path / "mirror.json"),
            "--preset-id",
            "p1_empire_transition",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out_presets.read_text(encoding="utf-8"))
    sidecar = json.loads(out_sidecar.read_text(encoding="utf-8"))
    assert sidecar["schema_version"] == "showroom_meaning_topology_qa_router_sidecar_v1"
    p1 = next(p for p in doc["presets"] if p["id"] == "p1_empire_transition")
    rp = p1.get("router_path_v1")
    assert rp is not None
    assert rp.get("schema_version") == "showroom_qa_router_path_v1"
    assert rp.get("note_ko") or rp.get("verse_refs") or rp.get("node_ids")
