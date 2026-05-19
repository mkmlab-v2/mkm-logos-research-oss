"""STEPBible TVTMS versification parser (offline when vault sparse clone present)."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TVTMS = (
    ROOT
    / "vault/external_lexicon/sources/stepbible-data/Versification"
    / "TVTMS - Translators Versification Traditions with Methodology for Standardisation for Eng+Heb+Lat+Grk+Others - STEPBible.org CC BY.txt"
)

pytestmark = pytest.mark.skipif(not TVTMS.is_file(), reason="STEPBible TVTMS not in vault")


def test_load_eng_to_greek_2cor_colophon() -> None:
    from scripts.logos_stepbible_versification_v1 import load_stepbible_eng_to_greek

    m = load_stepbible_eng_to_greek(TVTMS)
    assert m.get("2Cor.13.14") == "2Cor.13.13"


def test_expand_side_absent_returns_empty() -> None:
    from scripts.logos_stepbible_versification_v1 import _expand_side

    assert _expand_side("Absent") == []
    assert _expand_side("") == []


def test_stepbible_sblgnt_candidates_matt_1721() -> None:
    from scripts.logos_stepbible_versification_v1 import stepbible_sblgnt_candidates_for_mt_verse

    cands = stepbible_sblgnt_candidates_for_mt_verse("Matt.17.21")
    assert "Matt.17.20" in cands


def test_mt_wlc_1kgs_chapter_overflow() -> None:
    from scripts.logos_mt_wlc_verse_map_v1 import mt_verse_id_to_wlc_osis_candidates

    cands = mt_verse_id_to_wlc_osis_candidates("1Kgs.4.21")
    assert "1Kgs.5.1" in cands


def test_mt_wlc_ezek_chapter_overflow() -> None:
    from scripts.logos_mt_wlc_verse_map_v1 import mt_verse_id_to_wlc_osis_candidates

    cands = mt_verse_id_to_wlc_osis_candidates("Ezek.20.45")
    assert "Ezek.21.1" in cands
