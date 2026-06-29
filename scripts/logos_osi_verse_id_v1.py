"""Map Open Scripture Intelligence node ids → MKM canonical verse refs [HYPO]."""

from __future__ import annotations

from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

OSI_BOOK_SLUG: dict[str, str] = {
    "genesis": "Gen",
    "exodus": "Exod",
    "leviticus": "Lev",
    "numbers": "Num",
    "deuteronomy": "Deut",
    "joshua": "Josh",
    "judges": "Judg",
    "ruth": "Ruth",
    "1samuel": "1Sam",
    "2samuel": "2Sam",
    "1kings": "1Kgs",
    "2kings": "2Kgs",
    "1chronicles": "1Chr",
    "2chronicles": "2Chr",
    "ezra": "Ezra",
    "nehemiah": "Neh",
    "esther": "Esth",
    "job": "Job",
    "psalms": "Ps",
    "psalm": "Ps",
    "proverbs": "Prov",
    "ecclesiastes": "Eccl",
    "songofsolomon": "Song",
    "songofsongs": "Song",
    "isaiah": "Isa",
    "jeremiah": "Jer",
    "lamentations": "Lam",
    "ezekiel": "Ezek",
    "daniel": "Dan",
    "hosea": "Hos",
    "joel": "Joel",
    "amos": "Amos",
    "obadiah": "Obad",
    "jonah": "Jonah",
    "micah": "Mic",
    "nahum": "Nah",
    "habakkuk": "Hab",
    "zephaniah": "Zeph",
    "haggai": "Hag",
    "zechariah": "Zech",
    "malachi": "Mal",
    "matthew": "Matt",
    "mark": "Mark",
    "luke": "Luke",
    "john": "John",
    "acts": "Acts",
    "romans": "Rom",
    "1corinthians": "1Cor",
    "2corinthians": "2Cor",
    "galatians": "Gal",
    "ephesians": "Eph",
    "philippians": "Phil",
    "colossians": "Col",
    "1thessalonians": "1Thess",
    "2thessalonians": "2Thess",
    "1timothy": "1Tim",
    "2timothy": "2Tim",
    "titus": "Titus",
    "philemon": "Phlm",
    "hebrews": "Heb",
    "james": "Jas",
    "1peter": "1Pet",
    "2peter": "2Pet",
    "1john": "1John",
    "2john": "2John",
    "3john": "3John",
    "jude": "Jude",
    "revelation": "Rev",
}


def osi_node_id_to_canonical(raw: str) -> str:
    s = str(raw or "").strip()
    if not s:
        return ""
    parts = s.split("-")
    if len(parts) < 4:
        return canonical_verse_ref(s)
    verse = parts[-1]
    chapter = parts[-2]
    book_slug = "-".join(parts[1:-2]).replace("-", "")
    if not (verse.isdigit() and chapter.isdigit()):
        return ""
    book = OSI_BOOK_SLUG.get(book_slug.lower(), book_slug)
    return canonical_verse_ref(f"{book}.{chapter}.{verse}")
