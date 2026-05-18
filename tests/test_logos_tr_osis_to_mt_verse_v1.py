"""TR OSIS → MT verse_id mapping."""

from __future__ import annotations

from scripts.logos_tr_osis_to_mt_verse_v1 import honza_row_to_verse_id


def test_honza_row_to_verse_id_matt() -> None:
    vid = honza_row_to_verse_id(
        {"book_name_osis": "Matt", "chapter": 18, "verse": 11, "greek_text": "..."}
    )
    assert vid == "Matt.18.11"


def test_honza_row_john_maps_jhn() -> None:
    vid = honza_row_to_verse_id({"book_name_osis": "John", "chapter": 5, "verse": 4})
    assert vid == "Jhn.5.4"
