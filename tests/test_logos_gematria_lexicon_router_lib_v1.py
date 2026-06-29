"""Unit tests for gematria lexicon router lib (tiny fixture, no 24k load)."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.logos_gematria_lexicon_router_lib_v1 import (
    match_lexicon_hits,
    strongs_verse_ids_from_lemma,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/logos_gematria_lexicon_router_sample_v1.jsonl"

LEMMA_FIXTURE: list[dict] = [
    {
        "edge_type": "GNOSIS_STRONGS_CONTAIN",
        "strongs_number": "H7225",
        "dst_node_id": "Gen.1.1",
    },
    {
        "edge_type": "GNOSIS_STRONGS_CONTAIN",
        "strongs_number": "G3056",
        "dst_node_id": "John.1.1",
    },
    {
        "edge_type": "GNOSIS_STRONGS_CONTAIN",
        "strongs_number": "H2134",
        "dst_node_id": "Job.28.17",
    },
]


def _load_fixture_rows() -> list[dict]:
    rows: list[dict] = []
    for line in FIXTURE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def test_match_lexicon_hits_gloss_and_transliteration():
    rows = _load_fixture_rows()
    hits = match_lexicon_hits(["beginning", "logos", "pure"], rows, max_hits=15)
    strongs = {h["strongs"] for h in hits}
    assert "H7225" in strongs
    assert "G3056" in strongs
    assert "H2134" in strongs
    logos_hit = next(h for h in hits if h["strongs"] == "G3056")
    assert "logos" in logos_hit["match_tokens"]
    assert "transliteration" in logos_hit["match_fields"]


def test_match_lexicon_hits_strongs_token():
    rows = _load_fixture_rows()
    hits = match_lexicon_hits(["h7225"], rows, max_hits=5)
    assert len(hits) == 1
    assert hits[0]["strongs"] == "H7225"
    assert "strongs" in hits[0]["match_fields"]


def test_strongs_verse_ids_from_lemma():
    verses = strongs_verse_ids_from_lemma({"H7225", "G3056"}, LEMMA_FIXTURE, max_verses=20)
    assert "Gen.1.1" in verses
    assert "John.1.1" in verses


def test_strongs_verse_ids_respects_max():
    verses = strongs_verse_ids_from_lemma(
        {"H7225", "G3056", "H2134"},
        LEMMA_FIXTURE,
        max_verses=2,
    )
    assert len(verses) == 2
