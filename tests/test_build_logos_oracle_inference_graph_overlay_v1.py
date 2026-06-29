# Keywords: logos_oracle_inference_graph_overlay, L1-A, NON_GATING

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/build_logos_oracle_inference_graph_overlay_v1.py"


def test_runner_exists() -> None:
    assert RUNNER.is_file()


def test_build_overlay_smoke(tmp_path: Path) -> None:
    out = tmp_path / "overlay.json"
    r = subprocess.run(
        [sys.executable, str(RUNNER), "--out-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_oracle_inference_graph_overlay_v1"
    assert doc["research_only"] is True
    assert len(doc["four_d_families"]) == 4
    assert len(doc["pipeline_stages"]) == 5
    assert doc["l1a_phases"]["A1_four_d_families"] is True
    assert "verse" in doc["stage_by_node_kind"]
    assert doc["router_snapshot"]["boundary_ko"]
