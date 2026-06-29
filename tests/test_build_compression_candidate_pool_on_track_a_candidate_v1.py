"""Build compression candidate_pool_on Track A candidate artifact from grid SSOT."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GRID = ROOT / "reports/compression_41k_best_combo_grid_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/compression_candidate_pool_on_track_a_candidate_v1_latest.json"


@pytest.mark.skipif(not GRID.is_file(), reason="grid artifact missing")
def test_build_candidate_pool_on_artifact() -> None:
    from scripts.build_compression_candidate_pool_on_track_a_candidate_v1 import main

    rc = main([])
    assert rc == 0
    assert OUT.is_file()
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc.get("track_a_active_untouched") is True
    assert doc.get("send_gate") == "HOLD"
    rcfg = doc.get("run_config") or {}
    assert rcfg.get("enable_candidate_pool_expansion") is True
    assert rcfg.get("routing_profile") == "candidate_pool_on"
    gates = doc.get("gates") or {}
    assert gates.get("auto_promote_ready") is False
