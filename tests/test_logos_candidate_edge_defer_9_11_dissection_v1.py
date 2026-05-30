"""Smoke: defer 9·11 A-D dissection report builder."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_logos_candidate_edge_defer_9_11_dissection_v1.py"
OUT_JSON = ROOT / "reports" / "logos_candidate_edge_defer_9_11_dissection_v1_latest.json"


def test_defer_dissection_builder_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, str(BUILDER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert OUT_JSON.is_file()
    doc = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_candidate_edge_defer_9_11_dissection_v1"
    assert doc["research_only"] is True
    assert doc["merge_to_canonical_allowed"] is False
    ranks = {p["queue_rank"]: p for p in doc["pairs_analyzed"]}
    assert set(ranks) == {8, 9, 10, 11}
    assert ranks[9]["D_decision"]["recommendation"] == "defer_maintain"
    assert ranks[11]["D_decision"]["recommendation"] == "defer_maintain"
    assert ranks[8]["D_decision"]["recommendation"] == "approve_baseline_intra_genesis"
    assert ranks[9]["A_surface_text"]["src"]["text_hebrew_norm"]
    assert ranks[9]["B_embedding_neighbors"]["src_top6"]
