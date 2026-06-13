"""Cursor dogfood peer brief check smoke."""

from __future__ import annotations

from pathlib import Path

from scripts.check_a2a_cursor_dogfood_peer_brief_v1 import build_check


def test_peer_brief_check_ok():
    doc = build_check(Path(__file__).resolve().parents[1])
    assert doc["schema"] == "a2a_cursor_dogfood_peer_check_v1"
    assert doc["check_ok"] is True
    assert doc["failures"] == []
    assert len(doc["lanes"]) == 4
