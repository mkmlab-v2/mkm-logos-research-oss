"""P11 resonance_cap floor — SSOT may be >80 after P12; read-only floor gate."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLICE_ART = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bloom_slice_v1_latest.json"
SLICE_PUBLIC = (
    ROOT / "projects/mkm/mkm-life/public/data/logos_cosmic_anchor_graph_bloom_slice_v1.json"
)


def test_resonance_cap_at_least_eighty() -> None:
    for path in (SLICE_ART, SLICE_PUBLIC):
        doc = json.loads(path.read_text(encoding="utf-8"))
        cap = int(doc.get("resonance_cap") or 0)
        top_n = len(doc.get("resonance_edges_top") or [])
        assert cap >= 80
        assert top_n >= 80


def test_narrative_still_two_hundred() -> None:
    doc = json.loads(SLICE_PUBLIC.read_text(encoding="utf-8"))
    assert len(doc.get("narrative_path_samples") or []) >= 200
