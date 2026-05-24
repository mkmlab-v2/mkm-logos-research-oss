#!/usr/bin/env python3
"""Map scrollmapper bible_databases TR.json book names → MKM MT verse_id prefix."""

from __future__ import annotations

SCROLLMAPPER_BOOK_TO_MT: dict[str, str] = {
    "Matthew": "Matt",
    "Mark": "Mark",
    "Luke": "Luke",
    "John": "Jhn",
    "Acts": "Acts",
    "Romans": "Rom",
    "I Corinthians": "1Cor",
    "II Corinthians": "2Cor",
    "Galatians": "Gal",
    "Ephesians": "Eph",
    "Philippians": "Phil",
    "Colossians": "Col",
    "I Thessalonians": "1Thess",
    "II Thessalonians": "2Thess",
    "I Timothy": "1Tim",
    "II Timothy": "2Tim",
    "Titus": "Titus",
    "Philemon": "Phlm",
    "Hebrews": "Heb",
    "James": "Jas",
    "I Peter": "1Pet",
    "II Peter": "2Pet",
    "I John": "1John",
    "II John": "2John",
    "III John": "3John",
    "Jude": "Jude",
    "Revelation of John": "Rev",
}


def scrollmapper_verse_to_id(book_name: str, chapter: int, verse: int) -> str | None:
    book = SCROLLMAPPER_BOOK_TO_MT.get(str(book_name).strip())
    if not book:
        return None
    return f"{book}.{int(chapter)}.{int(verse)}"
