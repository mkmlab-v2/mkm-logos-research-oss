"""MT verse_id → morphhb WLC osisID candidates (partial, B-track)."""

from __future__ import annotations

from functools import lru_cache

from scripts.logos_stepbible_versification_v1 import load_stepbible_eng_to_hebrew


@lru_cache(maxsize=1)
def _stepbible_hebrew_map() -> dict[str, str]:
    return load_stepbible_eng_to_hebrew()


def mt_verse_id_to_wlc_osis_candidates(verse_id: str) -> list[str]:
    """Return WLC osisID candidates for an MT-style verse_id (first match wins in ingest)."""
    parts = verse_id.split(".")
    if len(parts) != 3:
        return [verse_id]
    book, ch_s, v_s = parts[0], parts[1], parts[2]
    try:
        ch, v = int(ch_s), int(v_s)
    except ValueError:
        return [verse_id]
    out = [verse_id]
    # Hebrew Bible Joel: Christian MT ch2:28+ = WLC Joel 3:1+
    if book == "Joel" and ch == 2 and v >= 28:
        out.append(f"Joel.3.{v - 27}")
    # KJV/Masoretic 1 Kings ch4 overflow → WLC chapter 5 (morphhb ends 1Kgs.4 at v20)
    if book == "1Kgs" and ch == 4 and v > 20:
        out.append(f"1Kgs.5.{v - 20}")
    # KJV Ezekiel 20:45+ → WLC Ezekiel 21:1+ (morphhb ends Ezek.20 at v44)
    if book == "Ezek" and ch == 20 and v > 44:
        out.append(f"Ezek.21.{v - 44}")
    sb = _stepbible_hebrew_map().get(verse_id)
    if sb and sb not in out:
        out.append(sb)
    return out
