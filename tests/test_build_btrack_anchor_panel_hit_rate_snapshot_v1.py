"""Smoke test for anchor hit-rate snapshot builder."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_snapshot_schema() -> None:
    from scripts.build_btrack_anchor_panel_hit_rate_snapshot_v1 import build_snapshot

    doc = build_snapshot()
    assert doc["schema"] == "btrack_anchor_panel_hit_rate_snapshot_v1"
    assert isinstance(doc.get("lanes"), list)
