"""Morphhb WLC index builder and lemma hint parsing (rail_morphhb)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

from scripts.build_morphhb_form_to_lemma_index import (  # noqa: E402
    build_index,
    strongs_hints_from_lemma,
)
from scripts.core.build_original_language_master_atoms import _normalize_token  # noqa: E402


def test_strongs_hints_from_lemma():
    assert strongs_hints_from_lemma("b/7225") == ["H7225"]
    assert strongs_hints_from_lemma("1254 a") == ["H1254"]
    assert strongs_hints_from_lemma("430") == ["H430"]
    assert strongs_hints_from_lemma("c/d/776") == ["H776"]
    assert strongs_hints_from_lemma("") == []


def test_build_index_fixture_surface_keys():
    fixture = REPO / "tests" / "fixtures" / "morphhb" / "gen11_fragment.xml"
    assert fixture.is_file()
    index, stats = build_index([fixture])
    assert stats["w_tokens"] == 3
    assert stats["unique_norm_keys"] >= 2
    br = _normalize_token("בָּרָ֣א")
    assert br in index
    row = index[br][0]
    assert row["lemma"] == "1254 a"
    assert row["strongs_hints"] == ["H1254"]


def test_map_morphhb_requires_index_or_skip():
    script_index = (
        REPO / "reports" / "constitution" / "btrack_pilot" / "morphhb_norm_to_lemma_index_latest.json"
    )
    if not script_index.is_file():
        pytest.skip("full morphhb index not built yet")
    data = json.loads(script_index.read_text(encoding="utf-8"))
    assert data.get("schema") == "morphhb_norm_to_lemma_index_v1"
    assert isinstance(data.get("index"), dict)
    assert data.get("stats", {}).get("w_tokens", 0) > 1000
