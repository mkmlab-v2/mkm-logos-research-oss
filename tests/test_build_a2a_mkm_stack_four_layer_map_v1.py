"""Four-layer MKM stack map builder smoke."""

from __future__ import annotations

from pathlib import Path

from scripts.build_a2a_mkm_stack_four_layer_map_v1 import (
    ROOT,
    _load_facts,
    build_brief_markdown,
    build_map_markdown,
)


def test_build_map_markdown_has_layers_and_track_a_split():
    facts = _load_facts(ROOT)
    md = build_map_markdown(facts)
    assert "INTERNAL ONLY" in md
    assert "105436" in md or str(facts.get("naive_tokens")) in md
    assert "FAIL-COMP-004" in md
    assert "openapi_token_compression_v2_draft.yaml" in md
    assert "Track A" in md


def test_build_brief_corrects_a2a_track_a_split():
    facts = _load_facts(ROOT)
    md = build_brief_markdown(facts)
    assert "3a. Track A" in md
    assert "A2A 행에 쓰지 않음" in md
    assert facts.get("naive_tokens") is not None
