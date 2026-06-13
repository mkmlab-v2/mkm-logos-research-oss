"""A2A IR draft builder smoke."""

from __future__ import annotations

from pathlib import Path

from scripts.build_a2a_inter_agent_encoding_ir_draft_v1 import build_ir_markdown

ROOT = Path(__file__).resolve().parents[1]


def test_build_ir_markdown_contains_bench_and_disclaimer():
    md, meta = build_ir_markdown(ROOT)
    assert meta["public_facing_approved"] is False
    assert "INTERNAL ONLY" in md
    assert "a2a_dialogue_bench_v1_latest.json" in md
    assert "Track A" in md
    assert "95%" in md  # kill-matrix mention
