#!/usr/bin/env python3
"""Map honza/textus-receptus book_name_osis → MKM MT verse_id book prefix."""

from __future__ import annotations

# honza gnt.flat.json uses OSIS-style book_name_osis; MKM NT uses Matt/Jhn/1Cor …
OSIS_TO_MT_BOOK: dict[str, str] = {
    "Matt": "Matt",
    "Mt": "Matt",
    "Mark": "Mark",
    "Mk": "Mark",
    "Mar": "Mark",
    "Luke": "Luke",
    "Lk": "Luke",
    "Luk": "Luke",
    "John": "Jhn",
    "Jn": "Jhn",
    "Jhn": "Jhn",
    "Acts": "Acts",
    "Act": "Acts",
    "Ac": "Acts",
    "Rom": "Rom",
    "Ro": "Rom",
    "1Cor": "1Cor",
    "1Co": "1Cor",
    "2Cor": "2Cor",
    "2Co": "2Cor",
    "Gal": "Gal",
    "Ga": "Gal",
    "Eph": "Eph",
    "Phil": "Phil",
    "Php": "Phil",
    "Col": "Col",
    "1Thess": "1Thess",
    "1Th": "1Thess",
    "2Thess": "2Thess",
    "2Th": "2Thess",
    "1Tim": "1Tim",
    "1Ti": "1Tim",
    "2Tim": "2Tim",
    "2Ti": "2Tim",
    "Titus": "Titus",
    "Tit": "Titus",
    "Phlm": "Phlm",
    "Phm": "Phlm",
    "Heb": "Heb",
    "Jas": "Jas",
    "Jam": "Jas",
    "1Pet": "1Pet",
    "1Pe": "1Pet",
    "2Pet": "2Pet",
    "2Pe": "2Pet",
    "1John": "1John",
    "1Jn": "1John",
    "2John": "2John",
    "2Jn": "2John",
    "3John": "3John",
    "3Jn": "3John",
    "Jude": "Jude",
    "Jud": "Jude",
    "Rev": "Rev",
    "Re": "Rev",
}


def honza_row_to_verse_id(row: dict) -> str | None:
    osis = str(row.get("book_name_osis") or row.get("book_name_short") or "").strip()
    book = OSIS_TO_MT_BOOK.get(osis)
    if not book:
        return None
    try:
        ch = int(row["chapter"])
        vs = int(row["verse"])
    except (KeyError, TypeError, ValueError):
        return None
    return f"{book}.{ch}.{vs}"
