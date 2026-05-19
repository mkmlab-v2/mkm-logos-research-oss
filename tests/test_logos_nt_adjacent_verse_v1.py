"""NT adjacent verse helpers."""

from __future__ import annotations

from scripts.logos_nt_adjacent_verse_v1 import (
    adjacent_mt_verse_ids,
    parse_mt_verse_id,
    pick_sblgnt_filled_neighbor,
)


def test_parse_and_adjacent() -> None:
    assert parse_mt_verse_id("Matt.18.11") == ("Matt", 18, 11)
    assert adjacent_mt_verse_ids("Matt.18.11") == ["Matt.18.9", "Matt.18.10", "Matt.18.12", "Matt.18.13"]


def test_pick_neighbor() -> None:
    index = {
        "Matt.18.10": {"decode_status": "bhs_sblgnt_v2_core", "vector_4d": {"S": 0.1, "L": 0.2, "K": 0.5, "M": 0.2}},
        "Matt.18.11": {"decode_status": "mt_canon_only_no_critical_text", "vector_4d": {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}},
    }
    hit = pick_sblgnt_filled_neighbor("Matt.18.11", index)
    assert hit is not None
    assert hit[0] == "Matt.18.10"
