"""Tests for deterministic logos reasoning path (showroom v4)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "compute_logos_reasoning_path_v1.py"
SLICE = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"


def test_compute_path_three_hop_hub_verse() -> None:
    assert SLICE.is_file()
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--graph-json",
            str(SLICE),
            "--seed-ids",
            "theme::imperial_transition",
            "aramaic::Dan.2.10",
            "regime::empire_transition",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(proc.stdout)
    assert doc["schema_version"] == "logos_reasoning_path_v1"
    assert len(doc["node_ids"]) >= 2
    assert doc["node_ids"][0] == "theme::imperial_transition"
    assert "aramaic::Dan.2.10" in doc["node_ids"]


def test_attach_paths_presets_has_reasoning_path() -> None:
    presets = (
        ROOT
        / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
        / "showroom_meaning_topology_qa_presets_v1.json"
    )
    assert presets.is_file()
    doc = json.loads(presets.read_text(encoding="utf-8"))
    with_path = [p for p in doc.get("presets", []) if p.get("reasoning_path_v1")]
    assert len(with_path) >= 3
